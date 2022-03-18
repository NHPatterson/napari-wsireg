import os
from pathlib import Path

import pytest
from wsireg.parameter_maps.preprocessing import ImagePreproParams

from napari_wsireg.data.tifffile_image import TiffFileWsiRegImage
from napari_wsireg.gui.dialogs.add_merge import AddMerge
from napari_wsireg.gui.dialogs.add_modality import AddModality

HERE = Path(os.path.dirname(__file__))

REASON = "private data"
SKIP_PRIVATE = True


@pytest.fixture
def pref_image(qtbot):
    rgb_im_path = HERE.parents[2] / "_tests" / "fixtures" / "rgb_im_8bit.tiff"

    dlg = AddModality(file_path=rgb_im_path, preprocessing=ImagePreproParams())
    qtbot.addWidget(dlg)
    yield dlg


@pytest.fixture
def pref_image_opt(qtbot):
    rgb_im_path = HERE.parents[2] / "_tests" / "fixtures" / "rgb_im_8bit.tiff"
    dlg = AddModality(
        file_path=rgb_im_path, preprocessing=ImagePreproParams(), tag="t1", spacing=0.5
    )
    qtbot.addWidget(dlg)
    yield dlg


@pytest.fixture
def pref_image_image_data(qtbot):
    rgb_im_path = HERE.parents[2] / "_tests" / "fixtures" / "rgb_im_8bit.tiff"
    image_data = TiffFileWsiRegImage(rgb_im_path)
    dlg = AddModality(
        file_path=rgb_im_path, preprocessing=ImagePreproParams(), image_data=image_data
    )
    qtbot.addWidget(dlg)
    yield dlg


@pytest.fixture
def pref_image_image_data_fl(qtbot):
    mc_im_path = HERE.parents[2] / "_tests" / "fixtures" / "mc_im_8bit.tiff"
    image_data = TiffFileWsiRegImage(mc_im_path)
    dlg = AddModality(
        file_path=mc_im_path, preprocessing=ImagePreproParams(), image_data=image_data
    )
    qtbot.addWidget(dlg)
    yield dlg


@pytest.fixture
def pref_attachment(qtbot):
    rgb_im_path = HERE.parents[2] / "_tests" / "fixtures" / "rgb_im_8bit.tiff"

    dlg = AddModality(
        file_path=rgb_im_path,
        attachment=True,
        attachment_tags=["a1", "a2", "a3"],
        image_spacings={"a1": 0.5, "a2": 0.75, "a3": 0.25},
    )
    qtbot.addWidget(dlg)
    yield dlg


@pytest.fixture
def pref_attachment_no_tags(qtbot):
    rgb_im_path = HERE.parents[2] / "_tests" / "fixtures" / "rgb_im_8bit.tiff"

    dlg = AddModality(
        file_path=rgb_im_path,
        attachment=True,
        image_spacings={"a1": 0.5, "a2": 0.75, "a3": 0.25},
    )
    qtbot.addWidget(dlg)
    yield dlg


@pytest.fixture
def add_merge_modality(qtbot):
    dlg = AddMerge(merge_str="ok1, ok2")
    qtbot.addWidget(dlg)
    yield dlg


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_add_modality_dialog_cancel(qtbot, pref_image):
    assert pref_image.completed is False
    pref_image.cancel_add.click()
    assert pref_image.completed is False


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_add_modality_dialog_continue_no_tag(qtbot, pref_image):
    assert pref_image.completed is False
    pref_image.add_mod_to_wsireg.click()
    assert pref_image.completed is False


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_add_modality_dialog_continue_add_tag(qtbot, pref_image):
    assert pref_image.completed is False
    pref_image.tag.setText("t1")
    pref_image.add_mod_to_wsireg.click()
    assert pref_image.completed is True


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_add_modality_dialog_import_tag_spacing(qtbot, pref_image_opt):
    assert pref_image_opt.tag.text() == "t1"
    assert pref_image_opt.spacing.text() == "0.5"


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_add_modality_dialog_with_image_data(qtbot, pref_image_image_data):
    assert pref_image_image_data.prepro_cntrl.image_type.currentText() == "Brightfield"


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_add_modality_dialog_with_image_data_fl(qtbot, pref_image_image_data_fl):
    assert (
        pref_image_image_data_fl.prepro_cntrl.image_type.currentText() == "Fluorescence"
    )


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_add_modality_dialog_create_combo(qtbot, pref_attachment):
    assert pref_attachment.attachment_combo.count() == 3
    qbox = pref_attachment._create_combo_group(["a1", "a2", "a3", "a4"])
    assert qbox.count() == 4


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_add_modality_dialog_no_attach(qtbot, pref_attachment_no_tags):
    assert pref_attachment_no_tags.completed is False


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_add_merge_modality_set_tag(qtbot, add_merge_modality):
    assert add_merge_modality.completed is False
    add_merge_modality.continue_add.click()
    assert add_merge_modality.completed is False
    add_merge_modality.merge_tag.setText("t1")
    add_merge_modality.continue_add.click()
    assert add_merge_modality.completed is True


@pytest.mark.skipif(SKIP_PRIVATE, reason=REASON)
def test_add_merge_modality_cancel(qtbot, add_merge_modality):
    assert add_merge_modality.completed is False
    add_merge_modality.cancel_add.click()
    assert add_merge_modality.completed is False
