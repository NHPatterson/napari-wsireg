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


class ModalityControl(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        widg_layout = QHBoxLayout()
        widg_layout.addStretch()
        widg_layout.setSpacing(0)
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

        self.sub_widg = QWidget()
        self.sub_widg.setMaximumHeight(175)
        self.sub_widg.setLayout(QVBoxLayout())
        self.layout().addWidget(self.mod_list)
        self.sub_widg.layout().addWidget(self.add_mod_btn)
        self.sub_widg.layout().addWidget(self.add_ach_btn)
        self.sub_widg.layout().addWidget(self.add_shp_btn)
        self.sub_widg.layout().addWidget(self.del_mod_btn)
        self.sub_widg.layout().addWidget(self.edt_mod_btn)
        self.layout().addWidget(self.sub_widg)
        widg_layout.addStretch()


def create_modality_item(item_name: str, item_color: str) -> QListWidgetItem:
    item = QListWidgetItem(item_name)
    item.setForeground(QColor(item_color))
    return item
