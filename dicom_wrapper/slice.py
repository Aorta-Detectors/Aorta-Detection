import numpy as np
from minio_path.utils import read_file
from pydicom.dataset import Dataset
from pydicom.filereader import dcmread

from .parser import PT


class DicomSlice:
    def __init__(self, record: Dataset, path: PT, slice_path: PT):
        self.record = record
        self.path = path
        self.slice_path = slice_path.joinpath(*record.ReferencedFileID[1:])

    def read_all(self) -> None | tuple[np.ndarray, tuple[float, float, float]]:
        slice_record = dcmread(read_file(self.slice_path))
        if hasattr(slice_record, "SliceLocation"):
            return slice_record.pixel_array, (
                slice_record.PixelSpacing[0],
                slice_record.PixelSpacing[1],
                slice_record.SliceLocation,
            )
        return None, None

    def read(self) -> None | np.ndarray:
        slice_record = dcmread(read_file(self.slice_path))
        if hasattr(slice_record, "SliceLocation"):
            return slice_record.pixel_array
        return None
