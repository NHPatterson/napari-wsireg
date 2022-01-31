from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Union

import dask.array as da
import numpy as np


class WsiRegImage(ABC):

    _path: Union[str, Path]

    # image data
    _dask_pyr: List[da.Array]
    _thumbnail: np.ndarray

    # image dimension information
    _shape: Tuple[int, int, int]
    _n_ch: int

    # channel information
    _channel_axis: int
    _is_rgb: bool
    _is_interleaved: bool
    _channel_names: List[str]
    _channel_colors: List[str]

    # scaling information
    _pixel_spacing: Union[Tuple[int, int], Tuple[float, float]]
    _thumbnail_spacing: Union[Tuple[int, int], Tuple[float, float]]

    @property
    def path(self) -> Union[str, Path]:
        return self._path

    @property
    def shape(self) -> Tuple[int, int, int]:
        return self._shape

    @property
    def n_ch(self) -> int:
        return self._n_ch

    @property
    def is_rgb(self) -> bool:
        return self._is_rgb

    @property
    def is_interleaved(self) -> bool:
        return self._is_interleaved

    @property
    def channel_axis(self) -> int:
        return self._channel_axis

    @property
    def pixel_spacing(self) -> Union[Tuple[int, int], Tuple[float, float]]:
        return self._pixel_spacing

    @property
    def thumbnail_spacing(self) -> Union[Tuple[int, int], Tuple[float, float]]:
        return self._thumbnail_spacing

    @property
    def channel_names(self) -> List[str]:
        return self._channel_names

    @property
    def channel_colors(self) -> List[str]:
        return self._channel_colors

    @property
    def dask_pyr(self) -> List[da.Array]:
        return self._dask_pyr

    @property
    def thumbnail(self) -> da.Array:
        return self._thumbnail

    @abstractmethod
    def _get_dask_pyr(self) -> List[da.Array]:
        pass

    @abstractmethod
    def _get_thumbnail(self) -> da.Array:
        pass

    def prepare_image_data(self):
        self._dask_pyr = self._get_dask_pyr()
        self._thumbnail = self._get_thumbnail()

        if self._is_rgb and not self._is_interleaved:
            self._dask_pyr = [np.rollaxis(p, 0, 3) for p in self._dask_pyr]
            self._thumbnail = np.rollaxis(self._thumbnail, 0, 3)

        self._get_thumbnail_spacing()

    def _get_thumbnail_spacing(self) -> None:
        if self._thumbnail is not None and self._dask_pyr is not None:
            thumbnail_size_ = self._thumbnail.shape[1]
            base_layer_size = self._dask_pyr[0].shape[1]
            thumbnail_scale = np.round(base_layer_size / thumbnail_size_, 0).astype(int)
            self._thumbnail_spacing = (
                float(self._pixel_spacing[0]) * thumbnail_scale,
                float(self._pixel_spacing[1]) * thumbnail_scale,
            )
