from pathlib import Path
from typing import Dict, List, Optional, Union

from qtpy.QtGui import QDoubleValidator
from qtpy.QtWidgets import (
    QComboBox,
    QDialog,
    QErrorMessage,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from wsireg.parameter_maps.preprocessing import ImagePreproParams

from napari_wsireg.data import CziWsiRegImage, TiffFileWsiRegImage
from napari_wsireg.gui.setup_sub.preprocessing import PreprocessingControl


class AddModality(QDialog):
    def __init__(
        self,
        file_path: [str, Path],
        spacing: Optional[Union[int, float]] = None,
        tag: Optional[str] = None,
        parent=None,
        mode: str = "load",
        attachment: bool = False,
        attachment_tags: Optional[List[str]] = None,
        image_data: Optional[Union[CziWsiRegImage, TiffFileWsiRegImage]] = None,
        image_spacings: Optional[Dict[str, Union[int, float]]] = None,
        preprocessing: Optional[ImagePreproParams] = None,
    ):
        super().__init__(parent=parent)
        box_layout = QVBoxLayout()

        input_widg = QWidget()
        form_layout = QFormLayout()

        self.spacing = QLineEdit()
        self.spacing.setValidator(QDoubleValidator())

        if not spacing:
            self.spacing.setText("1.0")
        else:
            self.spacing.setText(str(round(spacing, 5)))
            self.spacing.setStyleSheet("color:#00D100")

        self.image_data = image_data
        self.image_spacings = image_spacings

        self.tag = QLineEdit()

        if tag:
            self.tag.setText(tag)
            self.tag.setReadOnly(True)
            self.spacing.setReadOnly(True)

        form_layout.addRow("Image filepath", QLabel(Path(file_path).name))
        form_layout.addRow("Image tag (name)", self.tag)
        form_layout.addRow("Set image pixel spacing (μm)", self.spacing)

        if attachment:
            self.attachment_combo = self._create_combo_group(attachment_tags)
            if self.attachment_combo:
                form_layout.addRow("Set attachment modality", self.attachment_combo)
                self._pull_attach_spacing()
                self.attachment_combo.currentTextChanged.connect(
                    self._pull_attach_spacing
                )

        input_widg.setLayout(form_layout)
        self.prepro_cntrl = PreprocessingControl(in_dock=False)

        self.setLayout(box_layout)
        self.layout().addWidget(input_widg)

        if not attachment:
            self.layout().addWidget(self.prepro_cntrl)
            if preprocessing:
                self.prepro_cntrl._import_data(preprocessing)

        btn_widg = QWidget()
        bottom_btns = QHBoxLayout()
        if mode == "load":
            self.add_mod_to_wsireg = QPushButton("Add modality")
            self.cancel_add = QPushButton("Cancel add")
        elif mode == "edit":
            self.add_mod_to_wsireg = QPushButton("Finish edits")
            self.cancel_add = QPushButton("Cancel edits")

        bottom_btns.addWidget(self.cancel_add)
        bottom_btns.addWidget(self.add_mod_to_wsireg)
        btn_widg.setLayout(bottom_btns)
        self.layout().addWidget(btn_widg)
        self.completed = False

        self.cancel_add.clicked.connect(self._cancel)
        self.add_mod_to_wsireg.clicked.connect(self._add)

        self.add_mod_to_wsireg.setDefault(True)

        if self.image_data:
            # type checking says None has no attribute
            # but the if statement prevents us from ever getting here
            # if there is a None
            spacing = image_data.pixel_spacing[0]  # type: ignore
            self.spacing.setText(str(round(spacing, 5)))
            self.spacing.setStyleSheet("color:#00D100")
            self._set_default_prepro()

    def _create_combo_group(self, attachment_tags) -> QComboBox:
        if not attachment_tags:
            emsg = QErrorMessage(self)
            emsg.showMessage(
                "No modalities have been defined for attachment\n"
                "Please add images for registration prior to attaching"
            )
            self.close()
        else:
            combo_box = QComboBox()
            for tag in attachment_tags:
                combo_box.addItem(tag)
            return combo_box

    def _cancel(self) -> None:
        self.completed = False
        self.close()

    def _add(self) -> None:
        if len(self.tag.text()) == 0:
            emsg = QErrorMessage(self)
            emsg.showMessage("Modality has not been given a tag")
            self.tag.setFocus()
            return

        else:
            self.completed = True
            self.close()

    def _set_default_prepro(self) -> None:
        if self.image_data.is_rgb:
            self.prepro_cntrl._change_type("Brightfield")
        else:
            self.prepro_cntrl._change_type("Fluorescence")

    def _pull_attach_spacing(self) -> None:
        current_attach_mod = self.attachment_combo.currentText()
        spacing = self.image_spacings[current_attach_mod]
        self.spacing.setText(str(round(spacing, 5)))
        self.spacing.setStyleSheet("color:#00D100")
