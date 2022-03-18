from typing import Dict
import json
from napari.layers import Shapes
import numpy as np

NAPARI_TO_GJ_GEOMS = {
    "polygon": "Polygon",
    "line": "LineString",
    "path": "LineString",
    "rectangle": "Polygon",
}


def napari_shapes_to_qp_geojson(layer: Shapes, output_path: str) -> str:
    """napari layer to QuPath geojson

    Parameters
    ----------
    layer: napari.layers.Shapes
        napari shapes layer

    output_path: str
        path to the output file
    Returns
    -------
    str
        Output path of the

    """
    gj_data = []
    for idx in range(len(layer.data)):
        if layer.shape_type[idx] != "ellipse":
            gj_data.append(
                polygon_to_gj_geom(layer.data[idx], layer.name, layer.shape_type[idx])
            )

    with open(output_path, "w") as f:
        json.dump(gj_data, f, indent=1)

    return output_path


def polygon_to_gj_geom(polygon: np.ndarray, name: str, shape_type: str) -> Dict:
    """napari data to QuPath geojson schema"""
    geojson_type = "Feature"
    id = "annotation"
    geo_type = NAPARI_TO_GJ_GEOMS[shape_type]

    if geo_type == "Polygon":
        polygon = np.vstack([polygon, polygon[0, :]])
        polygon = [polygon[:, [1, 0]].tolist()]
    else:
        polygon = polygon[:, [1, 0]].tolist()

    properties = {
        "classification": {"name": name, "colorRGB": -1},
        "isLocked": False,
    }
    return {
        "type": geojson_type,
        "id": id,
        "geometry": {
            "type": geo_type,
            "coordinates": polygon,
        },
        "properties": properties,
    }
