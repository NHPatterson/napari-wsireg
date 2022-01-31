import os
from pathlib import Path

import dask.array as da
import pytest

from napari_wsireg.data import TiffFileWsiRegImage

# private data logic borrowed from https://github.com/cgohlke/tifffile/tests/test_tifffile.py
HERE = Path(os.path.dirname(__file__))
private_dir = HERE.parents[1] / "_tests" / "private_data"
fixtures_dir = HERE.parents[1] / "_tests" / "fixtures"

SKIP_PRIVATE = False
REASON = "private data"

if not private_dir.exists():
    SKIP_PRIVATE = True


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_TiffFileWsiRegImage_ome_mc_metadata():
    im_fp = private_dir / "czi_4ch_16bit.ome.tiff"
    tf_wsi = TiffFileWsiRegImage(im_fp)

    assert tf_wsi.shape[0] == 4
    assert len(tf_wsi.shape) == 3
    assert tf_wsi.is_rgb is False
    assert tf_wsi.pixel_spacing == (0.65, 0.65)
    assert tf_wsi.channel_axis == 0
    assert tf_wsi.is_interleaved is False
    assert tf_wsi.ome_metadata is not None
    assert tf_wsi.largest_series == 0
    assert tf_wsi.n_ch == 4
    assert tf_wsi.channel_names == ["DAPI", "EGFP", "DsRed", "Cy5"]


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_TiffFileWsiRegImage_ome_mc_data():
    print(private_dir)
    im_fp = private_dir / "czi_4ch_16bit.ome.tiff"
    tf_wsi = TiffFileWsiRegImage(im_fp)
    tf_wsi.prepare_image_data()

    assert im_fp == tf_wsi.path
    assert isinstance(tf_wsi.dask_pyr, list) is True
    assert isinstance(tf_wsi.dask_pyr[0], da.Array) is True
    assert isinstance(tf_wsi.thumbnail, da.Array) is True
    assert tf_wsi.dask_pyr[0].shape == tf_wsi.shape


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_TiffFileWsiRegImage_ome_rgb_non_interleaved_metadata():
    im_fp = private_dir / "czi_rgb.ome.tiff"
    tf_wsi = TiffFileWsiRegImage(im_fp)

    assert tf_wsi.shape[0] == 3
    assert len(tf_wsi.shape) == 3
    assert tf_wsi.is_rgb is True
    assert tf_wsi.pixel_spacing == (0.22033799848968316, 0.22033799848968316)
    assert tf_wsi.channel_axis == 0
    assert tf_wsi.is_interleaved is False
    assert tf_wsi.ome_metadata is not None
    assert tf_wsi.largest_series == 0
    assert tf_wsi.n_ch == 3
    assert tf_wsi.channel_names == ["TL Brightfield"]


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_TiffFileWsiRegImage_ome_rgb_non_interleaved_data():
    im_fp = private_dir / "czi_rgb.ome.tiff"
    tf_wsi = TiffFileWsiRegImage(im_fp)
    tf_wsi.prepare_image_data()

    assert isinstance(tf_wsi.dask_pyr, list) is True
    assert isinstance(tf_wsi.dask_pyr[0], da.Array) is True
    assert isinstance(tf_wsi.thumbnail, da.Array) is True
    assert tf_wsi.dask_pyr[0].shape == (
        tf_wsi.shape[1],
        tf_wsi.shape[2],
        tf_wsi.shape[0],
    )


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_TiffFileWsiRegImage_ome_rgb_interleaved_metadata():
    im_fp = private_dir / "ome_interleaved_rgb.ome.tiff"
    tf_wsi = TiffFileWsiRegImage(im_fp)

    assert tf_wsi.shape[2] == 3
    assert len(tf_wsi.shape) == 3
    assert tf_wsi.is_rgb is True
    assert tf_wsi.pixel_spacing == (0.65, 0.65)
    assert tf_wsi.channel_axis == 2
    assert tf_wsi.is_interleaved is True
    assert tf_wsi.ome_metadata is not None
    assert tf_wsi.largest_series == 0
    assert tf_wsi.n_ch == 3
    assert tf_wsi.channel_names == ["C01"]


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_TiffFileWsiRegImage_ome_rgb_interleaved_data():
    im_fp = private_dir / "ome_interleaved_rgb.ome.tiff"
    tf_wsi = TiffFileWsiRegImage(im_fp)
    tf_wsi.prepare_image_data()

    assert isinstance(tf_wsi.dask_pyr, list) is True
    assert isinstance(tf_wsi.dask_pyr[0], da.Array) is True
    assert isinstance(tf_wsi.thumbnail, da.Array) is True
    assert tf_wsi.dask_pyr[0].shape == tf_wsi.shape


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_TiffFileWsiRegImage_ndpi_rgb_interleaved_metadata():
    im_fp = private_dir / "rgb_ndpi.ndpi"
    tf_wsi = TiffFileWsiRegImage(im_fp)

    assert tf_wsi.shape[2] == 3
    assert len(tf_wsi.shape) == 3
    assert tf_wsi.is_rgb is True
    assert tf_wsi.pixel_spacing == (0.22536734877850897, 0.22536734877850897)
    assert tf_wsi.channel_axis == 2
    assert tf_wsi.is_interleaved is True
    assert tf_wsi.largest_series == 0
    assert tf_wsi.n_ch == 3
    assert tf_wsi.channel_names == ["C01 - RGB"]


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_TiffFileWsiRegImage_ndpi_rgb_interleaved_data():
    im_fp = private_dir / "rgb_ndpi.ndpi"
    tf_wsi = TiffFileWsiRegImage(im_fp)
    tf_wsi.prepare_image_data()

    assert isinstance(tf_wsi.dask_pyr, list) is True
    assert isinstance(tf_wsi.dask_pyr[0], da.Array) is True
    assert isinstance(tf_wsi.thumbnail, da.Array) is True
    assert tf_wsi.dask_pyr[0].shape == tf_wsi.shape


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_TiffFileWsiRegImage_svs_rgb_interleaved_metadata():
    im_fp = private_dir / "svs_rgb.svs"
    tf_wsi = TiffFileWsiRegImage(im_fp)

    assert tf_wsi.shape[2] == 3
    assert len(tf_wsi.shape) == 3
    assert tf_wsi.is_rgb is True
    assert tf_wsi.pixel_spacing == (0.2254, 0.2254)
    assert tf_wsi.channel_axis == 2
    assert tf_wsi.is_interleaved is True
    assert tf_wsi.largest_series == 0
    assert tf_wsi.n_ch == 3
    assert tf_wsi.channel_names == ["C01 - RGB"]


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_TiffFileWsiRegImage_svs_rgb_interleaved_data():
    im_fp = private_dir / "svs_rgb.svs"
    tf_wsi = TiffFileWsiRegImage(im_fp)
    tf_wsi.prepare_image_data()

    assert isinstance(tf_wsi.dask_pyr, list) is True
    assert isinstance(tf_wsi.dask_pyr[0], da.Array) is True
    assert isinstance(tf_wsi.thumbnail, da.Array) is True
    assert tf_wsi.dask_pyr[0].shape == tf_wsi.shape


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_TiffFileWsiRegImage_scn_rgb_interleaved_metadata():
    im_fp = private_dir / "scn_rgb.scn"
    tf_wsi = TiffFileWsiRegImage(im_fp)

    assert tf_wsi.shape[2] == 3
    assert len(tf_wsi.shape) == 3
    assert tf_wsi.is_rgb is True
    assert tf_wsi.pixel_spacing == (0.5, 0.5)
    assert tf_wsi.channel_axis == 2
    assert tf_wsi.is_interleaved is True
    assert tf_wsi.largest_series == 1
    assert tf_wsi.n_ch == 3
    assert tf_wsi.channel_names == ["C01 - RGB"]


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_TiffFileWsiRegImage_scn_rgb_interleaved_data():
    im_fp = private_dir / "scn_rgb.scn"
    tf_wsi = TiffFileWsiRegImage(im_fp)
    tf_wsi.prepare_image_data()

    assert isinstance(tf_wsi.dask_pyr, list) is True
    assert isinstance(tf_wsi.dask_pyr[0], da.Array) is True
    assert isinstance(tf_wsi.thumbnail, da.Array) is True
    assert tf_wsi.dask_pyr[0].shape == tf_wsi.shape


def test_TiffFileWsiRegImage_mc_non_ome_metadata():
    im_fp = fixtures_dir / "mc_im_8bit.tiff"

    tf_wsi = TiffFileWsiRegImage(im_fp)

    assert tf_wsi.shape[0] == 3
    assert len(tf_wsi.shape) == 3
    assert tf_wsi.is_rgb is False
    assert tf_wsi.pixel_spacing == (1.0, 1.0)
    assert tf_wsi.channel_axis == 0
    assert tf_wsi.is_interleaved is False
    assert tf_wsi.largest_series == 0
    assert tf_wsi.n_ch == 3
    assert tf_wsi.channel_names == ["C01", "C02", "C03"]


def test_TiffFileWsiRegImage_mc_non_ome_data():
    im_fp = fixtures_dir / "mc_im_8bit.tiff"

    tf_wsi = TiffFileWsiRegImage(im_fp)
    tf_wsi.prepare_image_data()

    assert isinstance(tf_wsi.dask_pyr, list) is True
    assert isinstance(tf_wsi.dask_pyr[0], da.Array) is True
    assert isinstance(tf_wsi.thumbnail, da.Array) is True
    assert tf_wsi.dask_pyr[0].shape == tf_wsi.shape


def test_TiffFileWsiRegImage_rgb_non_ome_metadata():
    im_fp = fixtures_dir / "rgb_im_8bit.tiff"

    tf_wsi = TiffFileWsiRegImage(im_fp)

    assert tf_wsi.shape[2] == 3
    assert len(tf_wsi.shape) == 3
    assert tf_wsi.is_rgb is True
    assert tf_wsi.pixel_spacing == (1.0, 1.0)
    assert tf_wsi.channel_axis == 2
    assert tf_wsi.is_interleaved is True
    assert tf_wsi.largest_series == 0
    assert tf_wsi.n_ch == 3
    assert tf_wsi.channel_names == ["C01 - RGB"]


def test_TiffFileWsiRegImage_rgb_non_ome_data():
    im_fp = fixtures_dir / "rgb_im_8bit.tiff"

    tf_wsi = TiffFileWsiRegImage(im_fp)
    tf_wsi.prepare_image_data()

    assert isinstance(tf_wsi.dask_pyr, list) is True
    assert isinstance(tf_wsi.dask_pyr[0], da.Array) is True
    assert isinstance(tf_wsi.thumbnail, da.Array) is True
    assert tf_wsi.dask_pyr[0].shape == tf_wsi.shape


def test_TiffFileWsiRegImage_sc_metadata():
    im_fp = fixtures_dir / "sc_im_8bit.tiff"

    tf_wsi = TiffFileWsiRegImage(im_fp)

    assert tf_wsi.shape[0] == 1
    assert len(tf_wsi.shape) == 3
    assert tf_wsi.is_rgb is False
    assert tf_wsi.pixel_spacing == (1.0, 1.0)
    assert tf_wsi.channel_axis == 0
    assert tf_wsi.is_interleaved is False
    assert tf_wsi.largest_series == 0
    assert tf_wsi.n_ch == 1
    assert tf_wsi.channel_names == ["C01"]


def test_TiffFileWsiRegImage_sc_data():
    im_fp = fixtures_dir / "sc_im_8bit.tiff"

    tf_wsi = TiffFileWsiRegImage(im_fp)
    tf_wsi.prepare_image_data()

    assert isinstance(tf_wsi.dask_pyr, list) is True
    assert isinstance(tf_wsi.dask_pyr[0], da.Array) is True
    assert isinstance(tf_wsi.thumbnail, da.Array) is True
    assert tf_wsi.dask_pyr[0].shape == tf_wsi.shape


def test_TiffFileWsiRegImage_sc_data_thumbnail():
    im_fp = fixtures_dir / "sc_im_8bit.tiff"
    tf_wsi = TiffFileWsiRegImage(im_fp)
    tf_wsi._get_thumbnail()

    assert isinstance(tf_wsi.dask_pyr, list) is True
    assert isinstance(tf_wsi.dask_pyr[0], da.Array) is True
    assert isinstance(tf_wsi.thumbnail, da.Array) is True
    assert tf_wsi.dask_pyr[0].shape == tf_wsi.shape
