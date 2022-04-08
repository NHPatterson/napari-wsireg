from typing import Any, Dict, Optional, List

from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QListWidget,
    QListWidgetItem,
)
from qtpy.QtCore import Qt
from superqt import QCollapsible
from wsireg.parameter_maps.preprocessing import ImagePreproParams


class QChannelItem(QListWidgetItem):
    def __init__(
        self,
        channel_name: str,
    ):
        super(QChannelItem, self).__init__()
        self.channel_name = channel_name
        self.setText(self.channel_name)
        self.setFlags(self.flags() | Qt.ItemIsEditable | Qt.ItemIsUserCheckable)
        self.setCheckState(1)


class PreprocessingControl(QGroupBox):
    def __init__(self, parent=None, in_dock: bool = True):
        super().__init__()
        if in_dock:
            self.setTitle("")
        else:
            self.setTitle("Preprocessing")

        self.setLayout(QVBoxLayout())

        mod_select_layout = QFormLayout()
        self.mod_in_prepro = QLabel("[none selected]")
        mod_select_layout.addRow("Selected modality", self.mod_in_prepro)

        self.image_type = QComboBox()
        self.image_type.addItem("Fluorescence")
        self.image_type.addItem("Brightfield")

        self.ch_indices_sub = QCollapsible()

        self.max_int_proj = QCheckBox()
        self.max_int_proj.setChecked(True)

        self.as_uint8 = QCheckBox()
        self.as_uint8.setChecked(True)

        self.contrast_enhance = QCheckBox()
        self.contrast_enhance.setChecked(False)

        self.invert_intensity = QCheckBox()
        self.invert_intensity.setChecked(False)

        self.rot_cc = QSpinBox()
        self.rot_cc.setMinimum(-345)
        self.rot_cc.setMaximum(345)
        self.rot_cc.setSingleStep(15)

        self.flip = QComboBox()
        self.flip.addItem("None")
        self.flip.addItem("Horizontal")
        self.flip.addItem("Vertical")

        self.downsampling = QSpinBox()
        self.downsampling.setMaximum(8)
        self.downsampling.setMinimum(1)
        self.downsampling.setValue(1)

        self.crop_to_mask_bbox = QCheckBox()
        self.crop_to_mask_bbox.setChecked(True)

        self.use_mask = QCheckBox()
        self.use_mask.setChecked(False)

        self.selection_widg = QTabWidget()
        int_widg = QWidget()
        spat_widg = QWidget()
        int_widg_top_level_layout = QHBoxLayout()
        int_box_layout = QVBoxLayout()
        int_left_top_layout = QFormLayout()
        int_right_layout = QFormLayout()
        int_left_top_layout.layout().addRow(QLabel("Image type"), self.image_type)

        self.channel_list = QListWidget()
        self.channel_list.setMaximumWidth(200)
        self.channel_list.setMaximumHeight(100)

        int_box_layout.addLayout(int_left_top_layout)
        channel_header = QLabel("<b>Channels: Use / Name</b>")
        int_box_layout.addWidget(channel_header)
        int_box_layout.addWidget(self.channel_list)
        int_right_layout.layout().addRow(
            QLabel("Max intensity projection"), self.max_int_proj
        )
        int_right_layout.layout().addRow(QLabel("Data to np.uint8"), self.as_uint8)
        int_right_layout.layout().addRow(
            QLabel("Enhance contrast"), self.contrast_enhance
        )
        int_right_layout.layout().addRow(
            QLabel("Invert intensity"), self.invert_intensity
        )
        int_widg_top_level_layout.addLayout(int_box_layout)
        int_widg_top_level_layout.addLayout(int_right_layout)
        int_widg.setLayout(int_widg_top_level_layout)
        self.spat_prepro_layout = QFormLayout()

        self.spat_prepro_layout.layout().addRow(QLabel("Rotation (cc)"), self.rot_cc)
        self.spat_prepro_layout.layout().addRow(QLabel("Coordinate flip"), self.flip)
        self.spat_prepro_layout.layout().addRow(
            QLabel("Downsample image"), self.downsampling
        )
        self.spat_prepro_layout.layout().addRow(
            QLabel("Crop to mask bounding box"), self.crop_to_mask_bbox
        )
        self.spat_prepro_layout.layout().addRow(
            QLabel("Use mask in reg."), self.use_mask
        )

        spat_widg.setLayout(self.spat_prepro_layout)

        # int_spat_layout.addLayout(int_layout)
        # int_spat_layout.addLayout(spat_layout)

        self.selection_widg.addTab(int_widg, "Intensity")
        self.selection_widg.addTab(spat_widg, "Spatial")

        if in_dock:
            self.layout().addLayout(mod_select_layout)

        self.layout().addWidget(self.selection_widg)

        self.image_type.currentTextChanged.connect(self._change_type)

    def _change_type(self, input_type: Optional[str] = None) -> None:
        if input_type:
            current_type = input_type
        else:
            current_type = str(self.image_type.currentText())

        if current_type == "Fluorescence":
            self.max_int_proj.setChecked(True)
            self.as_uint8.setChecked(True)
            self.contrast_enhance.setChecked(True)
            self.invert_intensity.setChecked(False)
        elif current_type == "Brightfield":
            self.max_int_proj.setChecked(False)
            self.as_uint8.setChecked(True)
            self.contrast_enhance.setChecked(False)
            self.invert_intensity.setChecked(True)

        self.image_type.setCurrentText(str(current_type))

    def _add_channels(
        self, channel_names: List[str], check_status: Optional[List[bool]] = None
    ):
        self.channel_list.clear()
        if check_status and channel_names:
            for channel, status in zip(channel_names, check_status):
                ch_item = QChannelItem(channel)
                status_flag = 2 if status else 0
                ch_item.setCheckState(status_flag)
                self.channel_list.addItem(ch_item)
        elif check_status:
            channel_names = [f"C{str(i).zfill(2)}" for i in range(len(check_status))]
            for channel, status in zip(channel_names, check_status):
                ch_item = QChannelItem(channel)
                status_flag = 2 if status else 0
                ch_item.setCheckState(status_flag)
                self.channel_list.addItem(ch_item)
        else:
            for channel in channel_names:
                ch_item = QChannelItem(channel)
                ch_item.setCheckState(2)
                self.channel_list.addItem(ch_item)

    def _ch_indices_to_status(self, channel_names: List[str], ch_indices: List[int]):
        if ch_indices:
            status = []
            for i in range(len(channel_names)):
                if i in ch_indices:
                    status.append(True)
                else:
                    status.append(False)
        else:
            status = [True for _ in range(len(channel_names))]

        return status

    def _import_data(
        self, preprocessing_data: ImagePreproParams, channel_names: List[str]
    ) -> None:
        # boolean
        self.max_int_proj.setChecked(preprocessing_data.max_int_proj)
        self.as_uint8.setChecked(preprocessing_data.as_uint8)
        self.contrast_enhance.setChecked(preprocessing_data.contrast_enhance)
        self.invert_intensity.setChecked(preprocessing_data.invert_intensity)
        self.crop_to_mask_bbox.setChecked(preprocessing_data.crop_to_mask_bbox)
        self.use_mask.setChecked(preprocessing_data.use_mask)

        # spinbox
        self.rot_cc.setValue(preprocessing_data.rot_cc)
        self.downsampling.setValue(preprocessing_data.downsampling)

        # combo
        if preprocessing_data.flip:
            if preprocessing_data.flip.name == "HORIZONTAL":
                self.flip.setCurrentText("Horizontal")
            elif preprocessing_data.flip.name == "VERTICAL":
                self.flip.setCurrentText("Vertical")
        else:
            self.flip.setCurrentText("None")

        if preprocessing_data.image_type == preprocessing_data.image_type.LIGHT:
            self.image_type.setCurrentText("Brightfield")
        else:
            self.image_type.setCurrentText("Fluorescence")

        # channel data
        status = self._ch_indices_to_status(
            channel_names, preprocessing_data.ch_indices
        )
        self._add_channels(channel_names, status)

        return preprocessing_data

    def _export_data(self) -> Dict[str, Any]:

        if self.image_type.currentText() == "Brightfield":
            image_type = "BF"
        else:
            image_type = "FL"

        if self.flip.currentText() == "Horizontal":
            flip_val = "h"
        elif self.flip.currentText() == "Vertical":
            flip_val = "v"
        else:
            flip_val = None

        ch_indices = []
        channel_names = []
        for ch_idx in range(self.channel_list.count()):
            ch_item = self.channel_list.item(ch_idx)
            channel_names.append(ch_item.text())
            if ch_item.checkState() == 2:
                ch_indices.append(ch_idx)

        if len(ch_indices) == 0:
            ch_indices = None

        preprocessing_params = {
            "image_type": image_type,
            "max_int_proj": self.max_int_proj.isChecked(),
            "as_uint8": self.as_uint8.isChecked(),
            "contrast_enhance": self.contrast_enhance.isChecked(),
            "invert_intensity": self.invert_intensity.isChecked(),
            "rot_cc": float(self.rot_cc.value()),
            "flip": flip_val,
            "downsampling": int(self.downsampling.value()),
            "crop_to_mask_bbox": self.crop_to_mask_bbox.isChecked(),
            "use_mask": self.use_mask.isChecked(),
            "ch_indices": ch_indices,
        }
        return preprocessing_params, channel_names
