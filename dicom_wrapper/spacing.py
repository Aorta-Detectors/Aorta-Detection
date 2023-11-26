from functools import singledispatch
from typing import Any

import numpy as np

from .cube import DicomCube

Spacing = tuple[float, float, float]


@singledispatch
def compute_spacing(data: Any, *args, **kwargs) -> Spacing:
    return (1.0, 1.0, 1.0)


@compute_spacing.register
def _compute_from_raw_spacings(data: np.ndarray) -> Spacing:
    spacing_x, spacing_y, spcing_z = (
        np.unique(data[:, 0]),
        np.unique(data[:, 1]),
        np.unique(np.diff(data[:, 2], axis=0).round(3), axis=0),
    )
    if (
        spacing_x.shape[0] != 1
        and spacing_y.shape[0] != 1
        and spcing_z.shape[0] != 1
    ):
        raise Exception(
            f"invalid unique spacing values: {spacing_x, spacing_y, spcing_z}"
        )
    return (spacing_x[0], spacing_y[0], spcing_z[0])


@compute_spacing.register
def _compute_from_dicom_cube(series_name: str, cube: DicomCube) -> Spacing:
    serieses = dict(cube.serieses_name)
    _, spacing = serieses[series_name].series_spacing_data
    return compute_spacing(spacing)


@compute_spacing.register
def _compute_all_from_dicom_cube(
    cube: DicomCube,
) -> dict[str, Spacing]:
    return {
        name: compute_spacing(series.series_spacing_data[1])
        for name, series in cube.serieses_name
    }
