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
    QLabel,
)
from qtpy.QtCore import Qt
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
        top_level_layout = QVBoxLayout()
        widg_layout = QHBoxLayout()
        widg_layout.addStretch()
        widg_layout.setSpacing(5)
        top_level_layout.setSpacing(5)

        self.setLayout(top_level_layout)
        self.setMaximumHeight(250)

        self.mod_list = QListWidget()
        self.mod_list.setMaximumHeight(120)
        self.mod_list.setSelectionMode(QAbstractItemView.ExtendedSelection)

        btn_font = QFont("Arial", 10)
        header_font = QFont("Arial", 12)
        from_file_label = QLabel("<b>From file</b>")
        self.add_mod_btn = QPushButton("+  Image")
        self.add_ach_btn = QPushButton("+  Attachment")
        self.add_shp_btn = QPushButton("+  Shape")
        self.add_msk_btn = QPushButton("+  Mask")

        self.del_mod_btn = QPushButton("-  Remove")
        self.clr_mod_btn = QPushButton("   Clear")
        self.edt_mod_btn = QPushButton("   Edit")

        from_file_label.setStyleSheet("text-align:left;")
        self.add_mod_btn.setStyleSheet("text-align:left;")
        self.add_ach_btn.setStyleSheet("text-align:left;")
        self.add_shp_btn.setStyleSheet("text-align:left;")
        self.add_msk_btn.setStyleSheet("text-align:left;")

        # self.del_mod_btn.setStyleSheet("text-align:left;")
        # self.edt_mod_btn.setStyleSheet("text-align:left;")

        from_file_label.setFont(header_font)
        self.add_mod_btn.setFont(btn_font)
        self.add_ach_btn.setFont(btn_font)
        self.add_shp_btn.setFont(btn_font)
        self.add_msk_btn.setFont(btn_font)

        self.del_mod_btn.setFont(btn_font)
        self.clr_mod_btn.setFont(btn_font)
        self.edt_mod_btn.setFont(btn_font)

        btn_layout = QVBoxLayout()
        btn_layout.addWidget(from_file_label)
        btn_layout.addWidget(self.add_mod_btn)
        btn_layout.addWidget(self.add_ach_btn)
        btn_layout.addWidget(self.add_shp_btn)
        btn_layout.addWidget(self.add_msk_btn)
        # btn_layout.addWidget(self.del_mod_btn)
        # btn_layout.addWidget(self.edt_mod_btn)
        widg_layout.addLayout(btn_layout)

        # mod list layout with header
        mod_list_layout = QVBoxLayout()
        mod_list_header_font = QFont("Arial", 12)
        mod_list_header_font.setItalic(True)
        mod_list_header_font.setBold(True)

        mod_list_header = QLabel()
        mod_list_header.setFont(mod_list_header_font)
        mod_list_header.setText("Graph images, attachments, & shapes")
        mod_list_header.setText(
            f'<font color="{IMAGES_COL}"><b>images</b></font> | '
            f'<font color="{ATTACHMENTS_COL}"><b>attachments</b> '
            f'</font>| <font color="{SHAPES_COL}"><b>shapes</b></font> | masks'
        )

        mod_list_layout.addWidget(mod_list_header)
        mod_list_header.setAlignment(Qt.AlignCenter)
        mod_list_layout.addWidget(self.mod_list)
        widg_layout.addLayout(mod_list_layout)

        nap_header = QLabel()
        nap_header.setText("<b>From <i>napari</i></b>")
        nap_header.setFont(header_font)
        from_nap_layout = QVBoxLayout()
        self.add_mod_nap_btn = QPushButton("+  Image")
        self.add_ach_nap_btn = QPushButton("+  Attachment")
        self.add_shp_nap_btn = QPushButton("+  Shape")
        self.add_msk_nap_btn = QPushButton("+  Mask")
        self.add_mod_nap_btn.setFont(btn_font)
        self.add_ach_nap_btn.setFont(btn_font)
        self.add_shp_nap_btn.setFont(btn_font)
        self.add_msk_nap_btn.setFont(btn_font)
        self.add_mod_nap_btn.setStyleSheet("text-align:left;")
        self.add_ach_nap_btn.setStyleSheet("text-align:left;")
        self.add_shp_nap_btn.setStyleSheet("text-align:left;")
        self.add_msk_nap_btn.setStyleSheet("text-align:left;")

        from_nap_layout.addWidget(nap_header)
        from_nap_layout.addWidget(self.add_mod_nap_btn)
        from_nap_layout.addWidget(self.add_ach_nap_btn)
        from_nap_layout.addWidget(self.add_shp_nap_btn)
        from_nap_layout.addWidget(self.add_msk_nap_btn)

        widg_layout.addLayout(from_nap_layout)
        edit_rm_layout = QHBoxLayout()
        self.edt_mod_btn.setMaximumWidth(100)
        self.clr_mod_btn.setMaximumWidth(100)
        self.del_mod_btn.setMaximumWidth(100)
        # edit_rm_layout.addSpacerItem()
        edit_rm_layout.addWidget(self.edt_mod_btn)
        edit_rm_layout.addWidget(self.clr_mod_btn)
        edit_rm_layout.addWidget(self.del_mod_btn)
        self.layout().addLayout(widg_layout)
        self.layout().addLayout(edit_rm_layout)
        widg_layout.addStretch()
        top_level_layout.addStretch()


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
