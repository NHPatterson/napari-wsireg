from typing import Tuple, Union

import numpy as np


def centered_transform(
    image_size: Tuple[int, int],
    image_spacing: Tuple[int, int],
    rotation_angle: Union[float, int],
) -> np.ndarray:
    angle = np.deg2rad(rotation_angle)

    sina = np.sin(angle)
    cosa = np.cos(angle)

    # build rot mat
    rot_mat = np.eye(3)
    rot_mat[0, 0] = cosa
    rot_mat[1, 1] = cosa
    rot_mat[1, 0] = sina
    rot_mat[0, 1] = -sina

    # recenter transform
    center_point = np.multiply(image_size, image_spacing) / 2
    center_point = np.append(center_point, 0)
    translation = center_point - np.dot(rot_mat, center_point)
    rot_mat[:2, 2] = translation[:2]

    return rot_mat


def centered_flip(
    image_size: Tuple[int, int],
    image_spacing: Tuple[int, int],
    direction: str,
) -> np.ndarray:
    angle = np.deg2rad(0)

    sina = np.sin(angle)
    cosa = np.cos(angle)

    # build rot mat
    rot_mat = np.eye(3)

    rot_mat[0, 0] = cosa
    rot_mat[1, 1] = cosa
    rot_mat[1, 0] = sina
    rot_mat[0, 1] = -sina

    if direction == "Vertical":
        rot_mat[0, 0] = -1
    else:
        rot_mat[1, 1] = -1

    # recenter transform
    center_point = np.multiply(image_size, image_spacing) / 2
    center_point = np.append(center_point, 0)
    translation = center_point - np.dot(rot_mat, center_point)
    rot_mat[:2, 2] = translation[:2]

    return rot_mat
