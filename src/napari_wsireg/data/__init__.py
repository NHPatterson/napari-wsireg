from string import Template

from .czi_image import CziWsiRegImage  # noqa: F401
from .tifffile_image import TIFFFILE_EXTS, TiffFileWsiRegImage  # noqa: F401
from .wsireg_image import WsiRegImage  # noqa: F401

FILE_ERROR_MESSAGE = Template(
    "The imported data file $file_path with extesnsion "
    "$ext does not match an acceptable "
    "tiff extension: \n[$tiff_ext] \nor .czi for Zeiss images"
)
