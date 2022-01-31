from qtpy.QtCore import Qt
from qtpy.QtGui import QFont
from qtpy.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget
from superqt.collapsible import QCollapsible

from napari_wsireg.gui.setup_sub.modality import ModalityControl
from napari_wsireg.gui.setup_sub.paths import RegistrationPathControl
from napari_wsireg.gui.setup_sub.preprocessing import PreprocessingControl
from napari_wsireg.gui.setup_sub.project import ProjectControl
from napari_wsireg.gui.utils.colors import (ATTACHMENTS_COL, IMAGES_COL,
                                            SHAPES_COL)


class SetupTab(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        setup_layout = QVBoxLayout()
        setup_layout.setSpacing(10)
        setup_layout.addStretch()
        setup_layout.setAlignment(Qt.AlignTop)
        self.setLayout(setup_layout)
        mod_header = QLabel()
        mod_header.setText(
            f'<font color="{IMAGES_COL}"><b>Registration images</b></font> | <font color="{ATTACHMENTS_COL}"><b>Attachment images</b> '
            f'</font>| <font color="{SHAPES_COL}"><b>Attachment shapes</b></font>'
        )

        mod_header.setFont(QFont("Arial", 14))
        mod_header.setAlignment(Qt.AlignTop)

        self.mod_ctrl = ModalityControl()
        self.prepro_ctrl = PreprocessingControl()
        self.path_ctrl = RegistrationPathControl()
        self.proj_ctrl = ProjectControl()

        self.layout().addWidget(mod_header)
        self.layout().setAlignment(mod_header, Qt.AlignTop)

        self.layout().addWidget(self.mod_ctrl)
        self.layout().setAlignment(self.mod_ctrl, Qt.AlignTop)

        self.prepro_collapse = QCollapsible(title="Preprocessing")
        self.prepro_collapse.addWidget(self.prepro_ctrl)
        self.layout().addWidget(self.prepro_collapse)
        self.layout().setAlignment(self.prepro_ctrl, Qt.AlignTop)

        reg_path_gbox = QGroupBox()
        reg_path_gbox.setTitle("Define registration paths")
        reg_path_gbox_layout = QVBoxLayout()
        reg_path_gbox_layout.setSpacing(5)
        reg_path_gbox.setLayout(reg_path_gbox_layout)
        reg_path_gbox.layout().addWidget(self.path_ctrl)
        self.layout().addWidget(reg_path_gbox)
        self.layout().setAlignment(reg_path_gbox, Qt.AlignTop)

        project_gbox = QGroupBox()
        project_gbox.setTitle("Save/queue/run registration graph")
        project_gbox.setLayout(QVBoxLayout())
        project_gbox.layout().addWidget(self.proj_ctrl)
        self.layout().addWidget(project_gbox)
        self.layout().setAlignment(project_gbox, Qt.AlignTop)
        setup_layout.addStretch()
        setup_layout.setSpacing(10)
