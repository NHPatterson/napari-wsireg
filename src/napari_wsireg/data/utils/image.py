from pathlib import Path
from typing import List, Tuple, Union

import numpy as np
import zarr
from dask import array as da
from tifffile import TiffFile, imread, xml2dict, imwrite


def tifffile_to_dask(
    im_fp: Union[str, Path], largest_series: int
) -> Union[da.Array, List[da.Array]]:
    imdata = zarr.open(imread(im_fp, aszarr=True, series=largest_series))
    if isinstance(imdata, zarr.hierarchy.Group):
        imdata = [da.from_zarr(imdata[z]) for z in imdata.array_keys()]
    else:
        imdata = da.from_zarr(imdata)
    return imdata


def guess_rgb(shape: Tuple[int, ...]) -> bool:
    """
    Guess if the passed shape comes from rgb data.
    If last dim is 3 or 4 assume the data is rgb, including rgba.

    Parameters
    ----------
    shape : list of int
        Shape of the data that should be checked.

    Returns
    -------
    bool
        If data is rgb or not.
    """
    ndim = len(shape)
    last_dim = shape[-1]
    if ndim > 2 and last_dim < 5:
        rgb = True
    else:
        rgb = False

    return rgb


def tf_get_largest_series(image_filepath: Union[str, Path]) -> int:
    """
    Determine largest series for .scn files by examining metadata
    For other multi-series files, find the one with the most pixels

    Parameters
    ----------
    image_filepath: str
        path to the image file

    Returns
    -------
    largest_series:int
        index of the largest series in the image data
    """
    fp_ext = Path(image_filepath).suffix.lower()
    tf_im = TiffFile(image_filepath)
    if fp_ext == ".scn":
        scn_meta = xml2dict(tf_im.scn_metadata)
        image_meta = scn_meta.get("scn").get("collection").get("image")
        largest_series = np.argmax(
            [
                im.get("scanSettings").get("objectiveSettings").get("objective")
                for im in image_meta
            ]
        )
    else:
        largest_series = np.argmax(
            [
                np.prod(np.asarray(series.shape), dtype=np.int64)
                for series in tf_im.series
            ]
        )
    return int(largest_series)


def zarr_get_base_pyr_layer(
    zarr_store: Union[zarr.hierarchy.Group, zarr.core.Array]
) -> zarr.core.Array:
    """
    Find the base pyramid layer of a zarr store

    Parameters
    ----------
    zarr_store
        zarr store

    Returns
    -------
    zarr_im: zarr.core.Array
        zarr array of base layer
    """
    if isinstance(zarr_store, zarr.hierarchy.Group):
        zarr_im = zarr_store[str(0)]
    elif isinstance(zarr_store, zarr.core.Array):
        zarr_im = zarr_store
    return zarr_im


def get_tifffile_info(
    image_filepath: Union[str, Path]
) -> Tuple[Tuple[int, int, int], np.dtype, int]:
    largest_series = tf_get_largest_series(image_filepath)
    zarr_im = zarr.open(imread(image_filepath, aszarr=True, series=largest_series))
    zarr_im = zarr_get_base_pyr_layer(zarr_im)
    im_dims = np.squeeze(zarr_im.shape)
    if len(im_dims) == 2:
        im_dims = np.concatenate([[1], im_dims])
    im_dtype = zarr_im.dtype

    return im_dims, im_dtype, largest_series


def compute_sub_res(
    zarray: da.Array, ds_factor: int, tile_size: int, is_rgb: bool, im_dtype: np.dtype
) -> da.Array:
    if is_rgb:
        resampling_axis = {0: 2**ds_factor, 1: 2**ds_factor, 2: 1}
        tiling = (tile_size, tile_size, 3)
    else:
        resampling_axis = {0: 1, 1: 2**ds_factor, 2: 2**ds_factor}
        tiling = (1, tile_size, tile_size)

    resampled_zarray_subres = da.coarsen(
        np.mean,
        zarray,
        resampling_axis,
        trim_excess=True,
    )
    resampled_zarray_subres = resampled_zarray_subres.astype(im_dtype)
    resampled_zarray_subres = resampled_zarray_subres.rechunk(tiling)

    return resampled_zarray_subres


def write_image_from_napari(
    image_data: Union[np.ndarray, da.Array, zarr.Array], output_fp: str
) -> str:
    imwrite(output_fp, image_data, compression="deflate", tile=(2048, 2048))
    return output_fp
