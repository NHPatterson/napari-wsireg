from typing import Union, Optional
from enum import Enum
from pathlib import Path
from qtpy.QtGui import QColor, QFont
from qtpy.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from napari_wsireg.gui.utils.colors import ATTACHMENTS_COL, IMAGES_COL, SHAPES_COL


class ModType(str, Enum):
    """Set the layer type for wsireg
    * "image": Registration image
    * "attachment": Image attached to registration image
    * "shape": shape set attached to registration image
    * "merge": modalities written to a single file at write time
    * "mask": mask attached to an image
    """

    IMAGE = "image"
    ATTACHMENT_IMAGE = "attachment"
    SHAPE = "shape"
    MERGE = "merge"
    MASK = "mask"


class QModalityListItem(QListWidgetItem):
    def __init__(
        self,
        mod_tag: str,
        mod_path: Union[str, Path],
        mod_spacing: float,
        mod_type: str,
        attachment_modality: Optional[str] = None,
    ):
        super(QModalityListItem, self).__init__()
        self.mod_tag = mod_tag
        self.mod_path = mod_path
        self.mod_spacing = mod_spacing
        self.mod_type = ModType[mod_type]
        self.attachment_modality = attachment_modality

        if self.mod_type == ModType.IMAGE:
            self.setForeground(QColor(IMAGES_COL))
        elif self.mod_type == ModType.ATTACHMENT_IMAGE:
            self.setForeground(QColor(ATTACHMENTS_COL))
        elif self.mod_type == ModType.SHAPE:
            self.setForeground(QColor(SHAPES_COL))
        else:
            pass


class ModalityControl(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        widg_layout = QHBoxLayout()
        widg_layout.addStretch()
        widg_layout.setSpacing(10)
        self.setMaximumHeight(200)

        self.setLayout(widg_layout)

        self.mod_list = QListWidget()
        self.mod_list.setMaximumHeight(120)
        self.mod_list.setSelectionMode(QAbstractItemView.ExtendedSelection)

        btn_font = QFont("Arial", 10)
        self.add_mod_btn = QPushButton("+  Image")
        self.add_ach_btn = QPushButton("+  Attachment")
        self.add_shp_btn = QPushButton("+  Shape")
        self.del_mod_btn = QPushButton("-  Remove")
        self.edt_mod_btn = QPushButton("   Edit")

        self.add_mod_btn.setStyleSheet("text-align:left;")
        self.add_ach_btn.setStyleSheet("text-align:left;")
        self.add_shp_btn.setStyleSheet("text-align:left;")
        self.del_mod_btn.setStyleSheet("text-align:left;")
        self.edt_mod_btn.setStyleSheet("text-align:left;")

        self.add_ach_btn.setFont(btn_font)
        self.add_shp_btn.setFont(btn_font)
        self.del_mod_btn.setFont(btn_font)
        self.add_mod_btn.setFont(btn_font)
        self.edt_mod_btn.setFont(btn_font)

        btn_layout = QVBoxLayout()

        self.layout().addWidget(self.mod_list)
        btn_layout.addWidget(self.add_mod_btn)
        btn_layout.addWidget(self.add_ach_btn)
        btn_layout.addWidget(self.add_shp_btn)
        btn_layout.addWidget(self.del_mod_btn)
        btn_layout.addWidget(self.edt_mod_btn)
        self.layout().addLayout(btn_layout)
        widg_layout.addStretch()


def create_modality_item(
    mod_tag: str,
    mod_path: Union[str, Path],
    mod_spacing: float,
    mod_type: str,
    display_name: str,
    attachment_modality: Optional[str] = None,
) -> QListWidgetItem:
    item = QModalityListItem(
        mod_tag, mod_path, mod_spacing, mod_type, attachment_modality
    )
    item.setText(display_name)
    return item
