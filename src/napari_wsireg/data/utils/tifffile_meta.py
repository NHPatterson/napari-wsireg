from typing import List, Tuple

from ome_types.model import OME
from pint import UnitRegistry
from tifffile import TiffFile


def tifftag_xy_pixel_sizes(
    rdr: TiffFile, series_idx: int, level_idx: int
) -> Tuple[float, float]:
    """Resolution data is stored in the TIFF tags in
    Pixels per cm, this is converted to microns per pixel
    """
    # pages are accessed because they contain the tiff tag
    # subset by series -> level -> first page contains all tags
    current_page = rdr.series[series_idx].levels[level_idx].pages[0]

    x_res = current_page.tags["XResolution"].value
    y_res = current_page.tags["XResolution"].value

    res_unit = current_page.tags["ResolutionUnit"].value

    # convert units to micron
    # res_unit == 1: undefined (px)
    # res_unit == 2 pixels per inch
    # res unit == 3 pixels per cm
    # in all cases we convert to um
    # https://www.awaresystems.be/imaging/tiff/tifftags/resolutionunit.html
    if res_unit.value == 1:
        res_to_um = 1
    if res_unit.value == 2:
        res_to_um = 25400
    elif res_unit.value == 3:
        res_to_um = 10000

    # conversion of pixels / um to um / pixel
    x_res_um = (1 / (x_res[0] / x_res[1])) * res_to_um
    y_res_um = (1 / (y_res[0] / y_res[1])) * res_to_um

    # correct for ITK assuming everything is spacing in mm
    software = current_page.tags.get("Software")
    if software and software.value == "InsightToolkit":
        x_res_um *= 0.001
        y_res_um *= 0.001

    return (x_res_um, y_res_um)


def svs_xy_pixel_sizes(
    rdr: TiffFile, series_idx: int, level_idx: int
) -> Tuple[float, float]:
    """Get resolution data stored in ImageDescription of SVS"""
    # pages are accessed because they contain the tiff tag
    # subset by series -> level -> first page contains all tags
    current_page = rdr.series[series_idx].levels[level_idx].pages[0]
    id_str = current_page.tags["ImageDescription"].value
    svs_info = id_str.split("|")
    mpp_val = None
    for i in svs_info:
        if "MPP" in i:
            mpp_val = float(i.split("=")[1])

    if mpp_val:
        return (mpp_val, mpp_val)
    else:
        return (1.0, 1.0)


def ometiff_xy_pixel_sizes(ome_metadata: OME, series_idx: int) -> Tuple[float, float]:
    ps_x = ome_metadata.images[series_idx].pixels.physical_size_x
    ps_y = ome_metadata.images[series_idx].pixels.physical_size_y
    ps_unit = ome_metadata.images[series_idx].pixels.physical_size_x_unit

    if ps_x and ps_y and ps_unit:
        if ps_unit.name.lower() != "micrometer":
            ureg = UnitRegistry()
            cur_size = ps_x * ureg(ps_unit.name.lower())
            out_um = cur_size.to("micrometer")
            ps_x_out = out_um.magnitude
            return (ps_x_out, ps_x_out)
        else:
            return (ps_x, ps_y)
    else:
        return (1.0, 1.0)


def ometiff_ch_names(ome_metadata: OME, series_idx: int) -> List[str]:
    ch_meta = ome_metadata.images[series_idx].pixels.channels
    cnames = []
    for idx, ch in enumerate(ch_meta):
        if ch.name:
            cnames.append(ch.name)
        else:
            cnames.append(f"C{str(idx + 1).zfill(2)}")

    return cnames
