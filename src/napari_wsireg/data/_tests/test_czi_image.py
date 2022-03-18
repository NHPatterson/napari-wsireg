import os
from pathlib import Path

import dask.array as da
import pytest

from napari_wsireg.data import CziWsiRegImage

# private data logic borrowed from
# https://github.com/cgohlke/tifffile/tests/test_tifffile.py
HERE = Path(os.path.dirname(__file__))
private_dir = HERE.parents[1] / "_tests" / "private_data"
fixtures_dir = HERE.parents[1] / "_tests" / "fixtures"

SKIP_PRIVATE = False
REASON = "private data"

if not private_dir.exists():
    SKIP_PRIVATE = True


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_CziWsiRegImage_mc_metadata():
    im_fp = private_dir / "czi_4ch_16bit.czi"
    czi_wsi = CziWsiRegImage(im_fp)

    assert czi_wsi.shape[0] == 4
    assert len(czi_wsi.shape) == 3
    assert czi_wsi.is_rgb is False
    assert czi_wsi.pixel_spacing == (0.65, 0.65)
    assert czi_wsi.channel_axis == 0
    assert czi_wsi.is_interleaved is False
    assert czi_wsi.n_ch == 4
    assert czi_wsi.channel_names == ["DAPI", "EGFP", "DsRed", "Cy5"]
    assert czi_wsi.channel_colors is not None


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_CziWsiRegImage_mc_data():
    im_fp = private_dir / "czi_4ch_16bit.czi"
    czi_wsi = CziWsiRegImage(im_fp)
    czi_wsi.prepare_image_data()

    assert isinstance(czi_wsi.dask_pyr, list) is True
    assert isinstance(czi_wsi.dask_pyr[0], da.Array) is True
    assert isinstance(czi_wsi.thumbnail, da.Array) is True
    assert czi_wsi.dask_pyr[0].shape == czi_wsi.shape


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_CziWsiRegImage_rgb_metadata():
    im_fp = private_dir / "czi_rgb.czi"
    czi_wsi = CziWsiRegImage(im_fp)

    assert czi_wsi.shape[2] == 3
    assert len(czi_wsi.shape) == 3
    assert czi_wsi.is_rgb is True
    assert czi_wsi.pixel_spacing == (0.22033799848968316, 0.22033799848968316)
    assert czi_wsi.channel_axis == 2
    assert czi_wsi.is_interleaved is True
    assert czi_wsi.n_ch == 3
    assert czi_wsi.channel_names == ["Brigh"]


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_CziWsiRegImage_rgb_data():
    im_fp = private_dir / "czi_rgb.czi"
    czi_wsi = CziWsiRegImage(im_fp)
    czi_wsi.prepare_image_data()
    czi_wsi._get_thumbnail()

    assert isinstance(czi_wsi.dask_pyr, list) is True
    assert isinstance(czi_wsi.dask_pyr[0], da.Array) is True
    assert isinstance(czi_wsi.thumbnail, da.Array) is True
    assert czi_wsi.dask_pyr[0].shape == czi_wsi.shape


def test_CziWsiRegImage_mc_metadata_mini():
    im_fp = fixtures_dir / "mini_czi_mc.czi"
    czi_wsi = CziWsiRegImage(im_fp)

    assert czi_wsi.shape[0] == 3
    assert len(czi_wsi.shape) == 3
    assert czi_wsi.is_rgb is False
    assert czi_wsi.pixel_spacing == (0.65, 0.65)
    assert czi_wsi.channel_axis == 0
    assert czi_wsi.is_interleaved is False
    assert czi_wsi.n_ch == 3
    assert czi_wsi.channel_names == ["DAPI", "EGFP", "DsRed"]
    assert czi_wsi.channel_colors is not None


def test_CziWsiRegImage_mc_data_mini():
    im_fp = fixtures_dir / "mini_czi_mc.czi"
    czi_wsi = CziWsiRegImage(im_fp)
    czi_wsi.prepare_image_data()
    czi_wsi._get_thumbnail()

    assert isinstance(czi_wsi.dask_pyr, list) is True
    assert isinstance(czi_wsi.dask_pyr[0], da.Array) is True
    assert isinstance(czi_wsi.thumbnail, da.Array) is True
    assert czi_wsi.dask_pyr[0].shape == czi_wsi.shape


def test_CziWsiRegImage_rgb_metadata_mini():
    im_fp = fixtures_dir / "mini_czi.czi"
    czi_wsi = CziWsiRegImage(im_fp)

    assert czi_wsi.shape[2] == 3
    assert len(czi_wsi.shape) == 3
    assert czi_wsi.is_rgb is True
    assert czi_wsi.pixel_spacing == (0.22033799848968316, 0.22033799848968316)
    assert czi_wsi.channel_axis == 2
    assert czi_wsi.is_interleaved is True
    assert czi_wsi.n_ch == 3
    assert czi_wsi.channel_names == ["Brigh"]


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_CziWsiRegImage_rgb_data_mini():
    im_fp = private_dir / "czi_rgb.czi"
    czi_wsi = CziWsiRegImage(im_fp)
    czi_wsi.prepare_image_data()
    czi_wsi._get_thumbnail()
    assert isinstance(czi_wsi.dask_pyr, list) is True
    assert isinstance(czi_wsi.dask_pyr[0], da.Array) is True
    assert isinstance(czi_wsi.thumbnail, da.Array) is True
    assert czi_wsi.dask_pyr[0].shape == czi_wsi.shape
    assert czi_wsi.thumbnail_spacing[0] > 0


def test_CziWsiRegImage_mc_thumbnail():
    im_fp = fixtures_dir / "mini_czi_mc.czi"
    czi_wsi = CziWsiRegImage(im_fp)
    czi_wsi.prepare_image_data()
    czi_wsi._get_thumbnail()

    assert czi_wsi.shape[0] == 3
    assert len(czi_wsi.shape) == 3
    assert czi_wsi.is_rgb is False
    assert czi_wsi.pixel_spacing == (0.65, 0.65)
    assert czi_wsi.channel_axis == 0
    assert czi_wsi.is_interleaved is False
    assert czi_wsi.n_ch == 3
    assert czi_wsi.channel_names == ["DAPI", "EGFP", "DsRed"]
    assert czi_wsi.channel_colors is not None
    assert czi_wsi.thumbnail_spacing[0] > 0
