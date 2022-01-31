from pathlib import Path
from typing import Optional, Union

from qtpy.QtWidgets import QFileDialog, QWidget

PathLike = Union[str, Path]


def open_file_dialog(
    parent_widg: QWidget,
    single: bool = True,
    wd: PathLike = "",
    name: str = "Open files",
    file_types: str = "All Files (*)",
) -> Optional[PathLike]:
    if single is False:
        file_path, _ = QFileDialog.getOpenFileNames(
            parent_widg,
            name,
            wd,
            file_types,
        )
    else:
        file_path, _ = QFileDialog.getOpenFileName(
            parent_widg,
            name,
            wd,
            file_types,
        )

    if file_path:
        return file_path
    else:
        return None
