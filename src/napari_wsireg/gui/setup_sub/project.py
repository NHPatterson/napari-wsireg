from qtpy.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)
from superqt import QCollapsible


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

        self.cache_images_check = QCheckBox()
        self.orig_size_check = QCheckBox()
        self.non_reg_image_check = QCheckBox()
        self.write_merge_and_indiv_check = QCheckBox()
        self.write_images_check = QCheckBox()

        self.orig_size_check.setChecked(False)
        self.non_reg_image_check.setChecked(True)
        self.write_merge_and_indiv_check.setChecked(False)
        self.cache_images_check.setChecked(True)
        self.write_images_check.setChecked(True)

        proj_entry_layout.addRow("Set project name", self.project_name_entry)
        proj_entry_layout.addRow(self.output_dir_select, self.output_dir_entry)
        proj_entry_layout.addRow("Write transformed images", self.write_images_check)

        adv_opts = QCollapsible("Advanced project options")
        adv_opts_widget = QWidget()
        adv_opts_layout = QFormLayout()
        adv_opts_layout.addRow("Cache prepro. images", self.cache_images_check)
        adv_opts_layout.addRow(
            "Write images to pre cropping size", self.orig_size_check
        )
        adv_opts_layout.addRow("Write non-transformed images", self.non_reg_image_check)
        adv_opts_layout.addRow(
            "Write merge and separate individual images",
            self.write_merge_and_indiv_check,
        )
        adv_opts_widget.setLayout(adv_opts_layout)
        adv_opts.addWidget(adv_opts_widget)
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
        self.layout().addWidget(adv_opts)
        self.layout().addLayout(action_layout)
