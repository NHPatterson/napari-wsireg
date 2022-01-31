from string import Template

FILE_ERROR_MESSAGE = Template(
    "The imported data file $file_path with extesnion $ext does not match an acceptable "
    "tiff extension: \n[$tiff_ext] \nor .czi for Zeiss images"
)
