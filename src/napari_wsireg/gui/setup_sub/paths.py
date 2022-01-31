from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class RegistrationPathControl(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        select_src = QWidget()
        select_src_layout = QFormLayout()
        select_src_layout.setSpacing(5)
        self.source_select = QComboBox()
        select_src_layout.addRow("Select source/moving modality", self.source_select)
        select_src.setLayout(select_src_layout)

        self.select_path_gbox = QGroupBox()
        self.select_path_gbox.setTitle("Define path to target/fixed")
        select_path_layout = QFormLayout()

        self.thru_select = QComboBox()
        self.target_select = QComboBox()

        self.reg_models = QComboBox()
        self.add_reg_model = QPushButton("Add reg model")

        self.current_reg_models = QLineEdit()
        self.current_reg_models.setReadOnly(True)
        self.current_reg_models.setStyleSheet(
            "background-color:rgb(38, 41, 48); border:0px"
        )
        self.current_reg_models.setText("[None added]")

        select_path_layout.addRow(
            "Select through modality (optional)", self.thru_select
        )
        select_path_layout.addRow("Select target/fixed modality", self.target_select)
        select_path_layout.addRow(self.reg_models, self.add_reg_model)
        select_path_layout.addRow("Reg. models for path", self.current_reg_models)

        self.select_path_gbox.setLayout(select_path_layout)

        self.add_reg_path = QPushButton("Add registration path")
        self.add_reg_path.setMinimumWidth(200)

        self.setLayout(main_layout)
        self.layout().addWidget(select_src)
        self.layout().addWidget(self.select_path_gbox)
        self.layout().addWidget(self.add_reg_path, alignment=Qt.AlignRight)
