from pathlib import Path
from typing import List

import dask.array as da
import numpy as np
import zarr
from tifffile import xml2dict

from napari_wsireg.data.utils.czi import CziRegImageReader, get_czi_thumbnail
from napari_wsireg.data.wsireg_image import WsiRegImage


class CziWsiRegImage(WsiRegImage):
    def __init__(self, image_filepath: [str, Path]):
        self._path = image_filepath
        self.czi = CziRegImageReader(self._path)

        self._get_dim_info()
        self._get_pixel_scaling()
        self._get_channel_metadata()

    def _get_pixel_scaling(self) -> None:
        czi_meta = xml2dict(self.czi.metadata())
        pixel_scaling_str = czi_meta["ImageDocument"]["Metadata"]["Scaling"]["Items"][
            "Distance"
        ][0]["Value"]
        pixel_scaling = float(pixel_scaling_str) * 1000000

        self._pixel_spacing = (pixel_scaling, pixel_scaling)

    def _get_channel_metadata(self) -> None:
        czi_meta = xml2dict(self.czi.metadata())
        channels_meta = czi_meta["ImageDocument"]["Metadata"]["DisplaySetting"][
            "Channels"
        ]["Channel"]

        if isinstance(channels_meta, dict):
            channels_meta = [channels_meta]

        cnames = []
        for ch in channels_meta:
            cnames.append(ch.get("ShortName"))

        self._channel_names = cnames

        ccolors = []
        for ch in channels_meta:
            ccolors.append(ch.get("Color"))

        self._channel_colors = ccolors

    def _get_dim_info(self) -> None:
        # if RGB need to get 0
        if self.czi.shape[-1] > 1:
            ch_dim_idx = self.czi.axes.index("0")
            self._is_rgb = True
            self._is_interleaved = True
        else:
            ch_dim_idx = self.czi.axes.index("C")
            self._is_rgb = False
            self._is_interleaved = False

        y_dim_idx = self.czi.axes.index("Y")
        x_dim_idx = self.czi.axes.index("X")

        if self.czi.shape[-1] > 1:
            im_dims = np.array(self.czi.shape)[[y_dim_idx, x_dim_idx, ch_dim_idx]]
        else:
            im_dims = np.array(self.czi.shape)[[ch_dim_idx, y_dim_idx, x_dim_idx]]

        n_ch = np.array(self.czi.shape)[[ch_dim_idx]]
        self._shape = (int(im_dims[0]), int(im_dims[1]), int(im_dims[2]))

        self._n_ch = int(n_ch)

        if self._is_rgb:
            self._channel_axis = len(self._shape) - 1
        else:
            self._channel_axis = 0

    def _get_dask_pyr(self) -> List[da.Array]:
        return self.czi.zarr_pyramidalize_czi(zarr.storage.TempStore())

    def _get_thumbnail(self) -> da.Array:

        thumbnail, thumbnail_spacing = get_czi_thumbnail(self.czi, self._pixel_spacing)

        if thumbnail_spacing:
            self._thumbnail = da.from_array(thumbnail, chunks=thumbnail.shape)
            self._thumbnail_spacing = thumbnail_spacing
        else:
            try:
                return self._dask_pyr[-1]
            except AttributeError:
                self.prepare_image_data()
                return self._get_thumbnail()
