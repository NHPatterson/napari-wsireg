from string import Template

from .czi_image import CziWsiRegImage
from .tifffile_image import TIFFFILE_EXTS, TiffFileWsiRegImage
from .wsireg_image import WsiRegImage

FILE_ERROR_MESSAGE = Template(
    "The imported data file $file_path with extesnion $ext does not match an acceptable "
    "tiff extension: \n[$tiff_ext] \nor .czi for Zeiss images"
)
