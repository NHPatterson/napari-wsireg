import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Union, Tuple

import dask.array as da
import numpy as np
import zarr
from czifile import CziFile
from tifffile import create_output

from napari_wsireg.data.utils.image import compute_sub_res, guess_rgb


class CziRegImageReader(CziFile):
    """
    Sub-class of CziFile with added functionality to only read certain channels
    """

    def sub_asarray(
        self,
        resize: bool = True,
        order: int = 0,
        out: Optional[np.ndarray] = None,
        max_workers: Optional[int] = None,
        zarr_fp: Optional[zarr.TempStore] = None,
    ) -> Union[np.ndarray, zarr.core.Array]:

        """Return image data from file(s) as numpy array.

        Parameters
        ----------
        resize : bool
            If True (default), resize sub/supersampled subblock data.
        order : int
            The order of spline interpolation used to resize sub/supersampled
            subblock data. Default is 0 (nearest neighbor).
        out : numpy.ndarray, str, or file-like object; optional
            Buffer where image data will be saved.
            If numpy.ndarray, a writable array of compatible dtype and shape.
            If str or open file, the file name or file object used to
            create a memory-map to an array stored in a binary file on disk.
        max_workers : int
            Maximum number of threads to read and decode subblock data.
            By default up to half the CPU cores are used.
        channel_idx : int or list of int
            The indices of the channels to extract
        as_uint8 : bool
            byte-scale image data to np.uint8 data type

        Parameters
        ----------
        out:np.ndarray
            image read with selected parameters as np.ndarray
        """

        out_shape = list(self.shape)
        start = list(self.start)

        out_dtype = self.dtype

        if zarr_fp is not None:
            rgb_chunk = self.shape[-1] if self.shape[-1] > 2 else 1
            root = zarr.open_group(zarr_fp, mode="a")
            pyramid_seq = str(0)
            chunking = (1, 1, 1, 2048, 2048, rgb_chunk)
            out = root.create_dataset(
                pyramid_seq,
                shape=tuple(out_shape),
                chunks=chunking,
                dtype=out_dtype,
                overwrite=True,
            )

        elif out is None:
            out = create_output(None, tuple(out_shape), out_dtype)

        if max_workers is None:
            max_workers = multiprocessing.cpu_count() - 1

        def func(directory_entry, resize=resize, order=order, start=start, out=out):
            """Read, decode, and copy subblock data."""
            subblock = directory_entry.data_segment()
            dvstart = list(directory_entry.start)
            tile = subblock.data(resize=resize, order=order)

            index = tuple(
                slice(i - j, i - j + k)
                for i, j, k in zip(tuple(dvstart), tuple(start), tile.shape)
            )

            try:
                out[index] = tile
            except ValueError as e:
                print("error")
                error = e
                corr_shape = (
                    str(error)
                    .split("shape ")[1]
                    .split(", got")[0]
                    .strip("(")
                    .strip(")")
                )
                corr_shape.split(",")
                cor_shape = tuple(slice(int(t)) for t in corr_shape.split(","))
                tile = tile[cor_shape]
                index = tuple(
                    slice(i - j, i - j + k)
                    for i, j, k in zip(tuple(dvstart), tuple(start), tile.shape)
                )
                out[index] = tile

        if max_workers > 1:
            self._fh.lock = True
            with ThreadPoolExecutor(max_workers) as executor:
                executor.map(func, self.filtered_subblock_directory)
            self._fh.lock = None
        else:

            for idx, directory_entry in enumerate(self.filtered_subblock_directory):
                func(directory_entry)

        if hasattr(out, "flush"):
            out.flush()
        return out

    def zarr_pyramidalize_czi(self, zarr_fp: zarr.TempStore) -> List[da.Array]:
        dask_pyr = []
        root = zarr.open_group(zarr_fp, mode="a")

        root.attrs["axes_names"] = list(self.axes)
        root.attrs["orig_shape"] = list(self.shape)
        all_axes = list(self.axes)
        yx_dims = np.where(np.isin(all_axes, ["Y", "X"]) == 1)[0].tolist()
        yx_shape = np.array(self.shape[slice(yx_dims[0], yx_dims[1] + 1)])

        ds = 1
        while np.min(yx_shape) // 2**ds >= 512:
            ds += 1

        self.sub_asarray(zarr_fp=zarr_fp, resize=True, order=0, max_workers=4)
        zarray = da.squeeze(da.from_zarr(zarr.open(zarr_fp)[0]))
        dask_pyr.append(da.squeeze(zarray))
        for ds_factor in range(1, ds):
            zres = zarr.storage.TempStore()
            rgb_chunk = self.shape[-1] if self.shape[-1] > 2 else 1
            is_rgb = True if rgb_chunk > 1 else False

            sub_res_image = compute_sub_res(zarray, ds_factor, 512, is_rgb, self.dtype)

            da.to_zarr(sub_res_image, zres, component="0")

            dask_pyr.append(da.squeeze(da.from_zarr(zres, component="0")))

        return dask_pyr


def get_level_blocks(czi: CziFile) -> dict:
    level_blocks = dict()
    for idx, sb in enumerate(czi.subblocks()):
        if sb.pyramid_type != 0:
            level = sb.shape[3] // sb.stored_shape[3]
        else:
            level = 0

        try:
            level_blocks[level]
        except KeyError:
            level_blocks[level] = dict()
            level_blocks[level] = [(idx, sb)]
            continue

        level_blocks[level].append((idx, sb))

    return level_blocks


def get_czi_thumbnail(
    czi: CziFile, pixel_spacing: Union[Tuple[int, int], Tuple[float, float]]
) -> Optional[Tuple[np.ndarray, Tuple[float, float]]]:
    ch_idx = czi.axes.index("C")
    l_blocks = get_level_blocks(czi)
    lowest_im = np.max(list(l_blocks.keys()))
    if lowest_im == 0:
        calc_thumbnail_spacing = np.asarray(pixel_spacing) * 1
    else:
        calc_thumbnail_spacing = np.asarray(pixel_spacing) * lowest_im

    thumbnail_spacing = (
        float(calc_thumbnail_spacing[0]),
        float(calc_thumbnail_spacing[1]),
    )

    block_indices = [b[0] for b in l_blocks[lowest_im]]
    if guess_rgb(czi.shape) and len(block_indices) == 1:
        data_idx = block_indices[0]
        image_data = czi.subblock_directory[data_idx].data_segment()
        thumbnail_array = np.squeeze(image_data.data(resize=False))
        return thumbnail_array, thumbnail_spacing

    elif len(block_indices) == czi.shape[czi.axes.index("C")]:
        thumbnail_shape = list(
            czi.subblock_directory[block_indices[0]].data_segment().stored_shape
        )
        thumbnail_shape[ch_idx] = czi.shape[ch_idx]

        thumbnail_array = np.empty(thumbnail_shape, dtype=czi.dtype)
        thumbnail_array = np.squeeze(thumbnail_array)
        for b_index in block_indices:
            image_data = czi.subblock_directory[b_index].data_segment()
            data_ch_index = [
                de.start for de in image_data.dimension_entries if de.dimension == "C"
            ][0]
            data = np.squeeze(image_data.data(resize=False))
            thumbnail_array[data_ch_index, :, :] = data

        return thumbnail_array, thumbnail_spacing

    else:
        return None, None
