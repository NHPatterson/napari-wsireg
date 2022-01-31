from qtpy.QtWidgets import (QDialog, QErrorMessage, QFormLayout, QLabel,
                            QLineEdit, QPushButton)


class AddMerge(QDialog):
    def __init__(
        self,
        merge_str: str,
        parent=None,
    ):
        super().__init__(parent=parent)
        form_layout = QFormLayout()
        self.cancel_add = QPushButton("Cancel merge setup")
        self.continue_add = QPushButton("Add merge")
        self.mod_to_merge = QLabel(merge_str)
        self.merge_tag = QLineEdit()
        form_layout.addRow("merger modalities (, separated)", self.mod_to_merge)
        form_layout.addRow(
            "Merge modality tag (propagates to filename)", self.merge_tag
        )
        form_layout.addRow(self.cancel_add, self.continue_add)
        self.setLayout(form_layout)

        self.completed = False

        self.cancel_add.clicked.connect(self._cancel)
        self.continue_add.clicked.connect(self._add)

    def _cancel(self) -> None:
        self.completed = False
        self.close()

    def _add(self) -> None:
        if len(self.merge_tag.text()) == 0:
            emsg = QErrorMessage(self)
            emsg.showMessage("Merge modality tag has not been provided")
            self.merge_tag.setFocus()
            return

        else:
            self.completed = True
            self.close()
