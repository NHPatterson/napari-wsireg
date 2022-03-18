from typing import Dict
from qtpy.QtWidgets import (
    QLabel,
    QAbstractItemView,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFormLayout,
)
from qtpy.QtGui import QColor
from wsireg import WsiReg2D


class QRegGraphListItem(QListWidgetItem):
    def __init__(
        self,
        queue_tag: str,
        reg_graph: WsiReg2D,
        reg_options: Dict,
    ):
        super(QRegGraphListItem, self).__init__()
        self.queue_tag = queue_tag
        self.reg_graph = reg_graph
        self.reg_options = reg_options
        self.finished = False

    def _set_finished(self):
        self.finished = True
        self.setForeground(QColor("green"))
        self.font().setItalic(True)


class QueueControl(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        main_layout = QVBoxLayout()
        list_layout = QHBoxLayout()
        list_side_layout = QVBoxLayout()
        bottom_layout = QHBoxLayout()
        current_running_layout = QFormLayout()

        self.queue_list = QListWidget()
        self.queue_list.setMaximumHeight(150)
        self.queue_list.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.queue_move_up_btn = QPushButton("↑")
        self.queue_move_down_btn = QPushButton("↓")
        self.queue_delete_btn = QPushButton("-")

        current_label = QLabel("Currently Running: ")
        self.current_running = QLabel()
        self.current_running.setText("[Not running]")
        current_running_layout.addRow(current_label, self.current_running)

        self.run_queue_btn = QPushButton("Run Queue")

        list_layout.addWidget(self.queue_list)
        list_side_layout.addWidget(self.queue_move_up_btn)
        list_side_layout.addWidget(self.queue_delete_btn)
        list_side_layout.addWidget(self.queue_move_down_btn)
        list_layout.addLayout(list_side_layout)

        bottom_layout.addWidget(self.run_queue_btn)

        main_layout.addLayout(list_layout)
        main_layout.addLayout(current_running_layout)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)


def generate_queue_tag(reg_graph):
    project_name = reg_graph.project_name
    output_dir = str(reg_graph.output_dir)
    queue_tag = f"{project_name} : {output_dir} : {reg_graph.n_modalities} modalities"
    return queue_tag


def reg_queue_item(reg_graph, reg_options) -> QListWidgetItem:

    queue_tag = generate_queue_tag(reg_graph)
    item = QRegGraphListItem(queue_tag, reg_graph, reg_options)
    item.setText(queue_tag)
    return item
