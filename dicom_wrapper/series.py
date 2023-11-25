from collections import namedtuple

import numpy as np
from pydicom.dataset import Dataset

from .parser import PT, make_hash
from .slice import DicomSlice

Series = namedtuple("Series", ["name", "data"])


class DicomSeries:
    def __init__(self, record: Dataset, path: PT, slice_path: PT):
        self.record = record
        self.description = (
            (str(record.SeriesDescription),)
            if hasattr(record, "SeriesDescription")
            else "No description"
        )
        self.number = str(record.SeriesNumber)
        self.slices = [
            DicomSlice(record, path, slice_path) for record in self.record.children
        ]

    def __str__(self) -> str:
        return f"{self.description}_{self.number}"

    @property
    def hash(self) -> str:
        return make_hash(self)

    @property
    def old_hash_mapping(self) -> tuple[str, str]:
        return self.description[0], str(self)

    @property
    def old_name_mapping(self) -> tuple[str, str]:
        return self.description[0], str(self)

    @property
    def series(self) -> Series:
        data = [slice_record.read_all() for slice_record in self.slices]
        frames = [(frame, spacing) for frame, spacing in data if (frame is not None) and (spacing is not None)]
        sorted_frames = sorted(frames, key=lambda x: x[1][2])
        data_frames = [frame[0] for frame in sorted_frames]
        if len(data_frames):
            data = np.stack(data_frames)
        else:
            data = []
        return Series(
            name=str(self),
            data=data,
        )

    @property
    def series_spacing_data(self) -> Series:
        data = [slice_record.read_all() for slice_record in self.slices]
        frames, spacing = zip(
            *[(frame, spacing) for frame, spacing in data if frame is not None]
        )
        if len(frames) and len(spacing):
            frames_array = np.stack(frames)
            spacing_array = np.array(spacing)
        else:
            frames_array = []
            spacing_array = []
        return frames_array, spacing_array
