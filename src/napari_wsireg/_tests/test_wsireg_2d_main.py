import os
from pathlib import Path

import pytest

from napari_wsireg._widget import WsiReg2DMain

HERE = Path(os.path.dirname(__file__))


@pytest.fixture
def wsi_reg_fixture(make_napari_viewer):
    # make viewer and add an image layer using our fixture
    viewer = make_napari_viewer()

    # create our widget, passing in the viewer
    wsireg2d = WsiReg2DMain(viewer)
    rgb_im_path = HERE / "fixtures" / "rgb_im_8bit.tiff"
    mc_im_path = HERE / "fixtures" / "mc_im_8bit.tiff"
    sc_im_path = HERE / "fixtures" / "sc_im_8bit.tiff"
    mc_czi_im_path = HERE / "fixtures" / "mini_czi_mc.czi"
    rgb_czi_im_path = HERE / "fixtures" / "mini_czi.czi"

    shape_fp = HERE / "fixtures" / "test-anno-data.geojson"

    wsireg2d.add_data("image", file_paths_in=rgb_im_path, no_dialog=True)
    wsireg2d.add_data("image", file_paths_in=mc_im_path, no_dialog=True)
    wsireg2d.add_data("image", file_paths_in=sc_im_path, no_dialog=True)
    wsireg2d.add_data("image", file_paths_in=mc_czi_im_path, no_dialog=True)
    wsireg2d.add_data("image", file_paths_in=rgb_czi_im_path, no_dialog=True)

    wsireg2d.add_data("attachment", file_paths_in=rgb_im_path, no_dialog=True)
    wsireg2d.add_data("attachment", file_paths_in=mc_im_path, no_dialog=True)
    wsireg2d.add_data("attachment", file_paths_in=sc_im_path, no_dialog=True)
    wsireg2d.add_data("attachment", file_paths_in=mc_czi_im_path, no_dialog=True)
    wsireg2d.add_data("attachment", file_paths_in=rgb_czi_im_path, no_dialog=True)

    wsireg2d.add_data("shape", file_paths_in=shape_fp, no_dialog=True)

    return wsireg2d


# make_napari_viewer is a pytest fixture that returns a napari viewer object
# capsys is a pytest fixture that captures stdout and stderr output streams
def test_WsiReg2DMain_add_modalities(wsi_reg_fixture, capsys):

    rgb_im_name = wsi_reg_fixture.image_mods[0]
    mc_im_name = wsi_reg_fixture.image_mods[1]
    sc_im_name = wsi_reg_fixture.image_mods[2]
    mc_czi_im_name = wsi_reg_fixture.image_mods[3]
    rgb_czi_im_name = wsi_reg_fixture.image_mods[4]

    att_rgb_im_name = wsi_reg_fixture.attachment_mods[0]
    att_mc_im_name = wsi_reg_fixture.attachment_mods[1]
    att_sc_im_name = wsi_reg_fixture.attachment_mods[2]
    att_mc_czi_im_name = wsi_reg_fixture.attachment_mods[3]
    att_rgb_czi_im_name = wsi_reg_fixture.attachment_mods[4]

    assert len(wsi_reg_fixture.image_mods) > 0
    assert wsi_reg_fixture.image_spacings[rgb_im_name] == 1.0
    assert wsi_reg_fixture.image_spacings[mc_im_name] == 1.0
    assert wsi_reg_fixture.image_spacings[sc_im_name] == 1.0
    assert wsi_reg_fixture.image_spacings[mc_czi_im_name] == 0.65
    assert wsi_reg_fixture.image_spacings[rgb_czi_im_name] == 0.22034
    assert wsi_reg_fixture.attachment_mods == [
        att_rgb_im_name,
        att_mc_im_name,
        att_sc_im_name,
        att_mc_czi_im_name,
        att_rgb_czi_im_name,
    ]


def test_wsireg_test_switching(wsi_reg_fixture):
    wsi_reg_fixture.current_mod_in_prepro.text()
    wsi_reg_fixture.reg_graph.modalities[wsi_reg_fixture.image_mods[0]]

    wsi_reg_fixture.mod_list.setCurrentRow(0)
    wsi_reg_fixture._switch_preprocessing_modality()
    wsi_reg_fixture.prepro_main_ctrl.image_type.setCurrentText("Brightfield")
    wsi_reg_fixture._update_preprocessing()
    wsi_reg_fixture.mod_list.setCurrentRow(1)
    wsi_reg_fixture._switch_preprocessing_modality()

    wsi_reg_fixture.mod_list.setCurrentRow(0)
    wsi_reg_fixture._switch_preprocessing_modality()

    assert wsi_reg_fixture.prepro_main_ctrl.image_type.currentText() == "Brightfield"

    wsi_reg_fixture.mod_list.setCurrentRow(1)
    wsi_reg_fixture._switch_preprocessing_modality()
    wsi_reg_fixture.prepro_main_ctrl.flip.setCurrentText("h")
    assert wsi_reg_fixture.prepro_main_ctrl.image_type.currentText() == "Fluorescence"


def test_wsireg_add_reg_path(wsi_reg_fixture):

    wsi_reg_fixture.mod_list.setCurrentRow(0)
    wsi_reg_fixture._switch_preprocessing_modality()

    wsi_reg_fixture.path_ctrl.source_select.setCurrentText(
        wsi_reg_fixture.image_mods[0]
    )
    wsi_reg_fixture.path_ctrl.target_select.setCurrentText(
        wsi_reg_fixture.image_mods[1]
    )

    wsi_reg_fixture.add_reg_path_to_graph()

    assert wsi_reg_fixture.reg_graph.reg_paths[wsi_reg_fixture.image_mods[0]] == [
        wsi_reg_fixture.image_mods[1]
    ]

    wsi_reg_fixture.path_ctrl.source_select.setCurrentText(
        wsi_reg_fixture.image_mods[0]
    )
    wsi_reg_fixture.path_ctrl.thru_select.setCurrentText(wsi_reg_fixture.image_mods[2])

    wsi_reg_fixture.path_ctrl.target_select.setCurrentText(
        wsi_reg_fixture.image_mods[1]
    )

    wsi_reg_fixture.add_reg_path_to_graph()

    assert wsi_reg_fixture.reg_graph.reg_paths[wsi_reg_fixture.image_mods[0]] == [
        wsi_reg_fixture.image_mods[2],
        wsi_reg_fixture.image_mods[1],
    ]


def test_wsireg_reg_path_switching(wsi_reg_fixture):
    wsi_reg_fixture.mod_list.setCurrentRow(0)
    wsi_reg_fixture._switch_preprocessing_modality()

    wsi_reg_fixture.path_ctrl.source_select.setCurrentText(
        wsi_reg_fixture.image_mods[0]
    )
    wsi_reg_fixture._update_path_possibilties()
    wsi_reg_fixture.path_ctrl.thru_select.setCurrentText(wsi_reg_fixture.image_mods[1])
    wsi_reg_fixture._update_paths_on_through()

    assert (
        wsi_reg_fixture.path_ctrl.target_select.currentText()
        != wsi_reg_fixture.image_mods[1]
    )

    wsi_reg_fixture.path_ctrl.thru_select.setCurrentText("None")
    wsi_reg_fixture._update_paths_on_through()
    wsi_reg_fixture.path_ctrl.target_select.setCurrentText(
        wsi_reg_fixture.image_mods[1]
    )
    wsi_reg_fixture._update_paths_on_target()

    assert (
        wsi_reg_fixture.path_ctrl.target_select.currentText()
        == wsi_reg_fixture.image_mods[1]
    )
