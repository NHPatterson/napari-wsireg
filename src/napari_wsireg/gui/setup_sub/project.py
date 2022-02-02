from qtpy.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ProjectControl(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        proj_entry_layout = QFormLayout()

        self.project_name_entry = QLineEdit()
        self.output_dir_select = QPushButton("Select output dir")
        self.output_dir_entry = QLineEdit()
        self.output_dir_entry.setReadOnly(True)
        self.output_dir_entry.setStyleSheet(
            "background-color:rgb(38, 41, 48); border:0px"
        )

        proj_entry_layout.addRow("Set project name", self.project_name_entry)
        proj_entry_layout.addRow(self.output_dir_select, self.output_dir_entry)

        action_layout = QHBoxLayout()

        self.write_config = QPushButton("Save config")
        self.add_to_queue = QPushButton("Add to queue")
        self.run_reg = QPushButton("Run graph")
        self.write_config.setMinimumWidth(100)
        self.add_to_queue.setMinimumWidth(100)
        self.run_reg.setMinimumWidth(100)

        action_layout.addWidget(self.write_config)
        action_layout.addWidget(self.add_to_queue)
        action_layout.addWidget(self.run_reg)

        self.layout().addLayout(proj_entry_layout)
        self.layout().addLayout(action_layout)
