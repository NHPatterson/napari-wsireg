import warnings
from pathlib import Path
from typing import List, Optional, Tuple

import dask.array as da
import numpy as np
from ome_types import from_xml
from ome_types.model import OME
from tifffile import TiffFile

from napari_wsireg.data.utils.image import (
    compute_sub_res,
    get_tifffile_info,
    guess_rgb,
    tifffile_to_dask,
)
from napari_wsireg.data.utils.tifffile_meta import (
    ometiff_ch_names,
    ometiff_xy_pixel_sizes,
    svs_xy_pixel_sizes,
    tifftag_xy_pixel_sizes,
)
from napari_wsireg.data.wsireg_image import WsiRegImage

TIFFFILE_EXTS = [".scn", ".ome.tiff", ".tif", ".tiff", ".svs", ".ndpi"]


class TiffFileWsiRegImage(WsiRegImage):
    ome_metadata: Optional[OME] = None

    def __init__(self, image_filepath: [str, Path]):

        self._path = image_filepath
        self.tf = TiffFile(self._path)

        (self._shape, _, self.largest_series) = self._get_image_info()
        self._get_dim_info()

        pix_spacing = self._get_pixel_spacing()
        self._pixel_spacing = (pix_spacing, pix_spacing)

        self._channel_names = self._get_ch_names()

    def _get_dim_info(self) -> None:
        if self._shape:
            if self.tf.ome_metadata:
                self.ome_metadata = from_xml(self.tf.ome_metadata)
                spp = (
                    self.ome_metadata.images[self.largest_series]
                    .pixels.channels[0]
                    .samples_per_pixel
                )
                interleaved = self.ome_metadata.images[
                    self.largest_series
                ].pixels.interleaved

                if spp and spp > 1:
                    self._is_rgb = True
                else:
                    self._is_rgb = False

                if guess_rgb(self._shape) is False:
                    self._channel_axis = 0
                    self._is_interleaved = False
                elif interleaved and guess_rgb(self._shape):
                    self._is_interleaved = True
                    self._channel_axis = len(self._shape) - 1

            else:
                self._is_rgb = guess_rgb(self._shape)
                self._is_interleaved = self._is_rgb
                if self._is_rgb:
                    self._channel_axis = len(self._shape) - 1
                else:
                    self._channel_axis = 0

            self._n_ch = self._shape[self._channel_axis]

    def _get_dask_pyr(self) -> List[da.Array]:
        dask_pyr = tifffile_to_dask(self._path, self.largest_series)
        if isinstance(dask_pyr, da.Array):
            dask_pyr = [dask_pyr]
        else:
            dask_pyr = dask_pyr

        dask_pyr = [
            d.reshape(1, *d.shape) if len(d.shape) == 2 else d for d in dask_pyr
        ]

        return dask_pyr

    def _get_thumbnail(self) -> da.Array:
        try:
            if len(self._dask_pyr) > 1:
                return self._dask_pyr[-1]
            else:
                is_rgb = True if self._channel_axis != 0 else False
                return compute_sub_res(
                    self._dask_pyr[0], 4, 512, is_rgb, self._dask_pyr[0].dtype
                )
        except AttributeError:
            self.prepare_image_data()
            self._get_thumbnail()

    def _get_pixel_spacing(self) -> float:
        if Path(self._path).suffix.lower() in [".scn", ".ndpi"]:
            return tifftag_xy_pixel_sizes(
                self.tf,
                self.largest_series,
                0,
            )[0]
        elif Path(self._path).suffix.lower() in [".svs"]:
            return svs_xy_pixel_sizes(
                self.tf,
                self.largest_series,
                0,
            )[0]
        elif self.tf.ome_metadata:
            return ometiff_xy_pixel_sizes(
                from_xml(self.tf.ome_metadata),
                self.largest_series,
            )[0]
        else:
            try:
                return tifftag_xy_pixel_sizes(
                    self.tf,
                    self.largest_series,
                    0,
                )[0]
            except KeyError:
                warnings.warn(
                    "Unable to parse pixel resolution information from file"
                    " defaulting to 1"
                )
                return 1.0

    def _get_ch_names(self) -> List[str]:
        if self.tf.ome_metadata:
            cnames = ometiff_ch_names(
                from_xml(self.tf.ome_metadata), self.largest_series
            )
        else:
            cnames = []
            if self.is_rgb:
                cnames.append("C01 - RGB")
            else:
                for idx, ch in enumerate(range(self.n_ch)):
                    cnames.append(f"C{str(idx + 1).zfill(2)}")

        return cnames

    def _get_image_info(self) -> Tuple[Tuple[int, int, int], np.dtype, int]:
        if len(self.tf.series) > 1:
            warnings.warn(
                "The tiff contains multiple series, "
                "the largest series will be read by default"
            )

        im_dims, im_dtype, largest_series = get_tifffile_info(self._path)

        im_dims = (int(im_dims[0]), int(im_dims[1]), int(im_dims[2]))

        return im_dims, im_dtype, largest_series
