from pathlib import Path
from typing import Optional, Union

from qtpy.QtWidgets import QFileDialog, QWidget

PathLike = Union[str, Path]


def open_file_dialog(
    parent_widg: QWidget,
    single: bool = True,
    wd: PathLike = "",
    data_type: str = "image",
    file_types: Optional[str] = "All Files (*)",
) -> Optional[PathLike]:

    if data_type == "image":
        name = "Open registration image(s)..."
        file_types = (
            "images (*.tiff *.tif *.svs *.ndpi *.scn *.czi);;"
            "Zeiss Czi (*.czi);;All Files (*)"
        )

    elif data_type == "attachment":
        name = "Open attachment image..."
        file_types = (
            "tifffile images (*.tiff *.tif *.svs *.ndpi *.scn *.czi);;"
            "Zeiss Czi (*.czi);;All Files (*)"
        )

    elif data_type == "shape":
        name = "Open attachment shape data..."
        file_types = "geojson files (*.geojson *.json);;All Files (*)"

    else:
        name = "Open file(s)..."
        file_types = file_types

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
