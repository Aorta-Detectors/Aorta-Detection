from typing import Generator

from pydicom.dataset import Dataset

from .parser import PT, make_hash
from .series import DicomSeries, Series


class DicomStudy:
    def __init__(self, record: Dataset, path: PT, slice_path: PT):
        self.record = record
        self.description = str(record.StudyDescription)
        self.date = str(record.StudyDate)
        self.time = str(record.StudyTime)
        self._serieses = [
            DicomSeries(record, path, slice_path) for record in self.record.children
        ]

    def __str__(self) -> str:
        return f"{self.description}_{self.date}_{self.time}"

    @property
    def hash(self) -> str:
        return make_hash(self)

    @property
    def series_names(self) -> Generator[tuple[str, DicomSeries], None, None]:
        for series in self._serieses:
            yield (f"{self}_{series}", series)

    @property
    def old_hash_mapping(self) -> Generator[tuple[str, str], None, None]:
        for series in self._serieses:
            old_name, new_name = series.old_hash_mapping
            yield (f"{self.description}:{old_name}", f"{self}_{new_name}")

    @property
    def old_name_mapping(self) -> Generator[tuple[str, str], None, None]:
        for series in self._serieses:
            old_name, new_name = series.old_name_mapping
            yield (f"{self.description} {old_name}".lstrip(" "), f"{self}_{new_name}")

    @property
    def serieses(self) -> Generator[Series, None, None]:
        for series in self._serieses:
            yield Series(f"{self}_{series.series.name}", series.series.data)
