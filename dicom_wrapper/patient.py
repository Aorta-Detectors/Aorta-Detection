from typing import Generator

from pydicom.dataset import Dataset

from .parser import PT, make_hash
from .series import DicomSeries, Series
from .study import DicomStudy


class DicomPatient:
    def __init__(self, record: Dataset, path: PT, slice_path: PT):
        self.record = record
        self.name = str(record.PatientName)
        self.studies = [
            DicomStudy(record, path, slice_path)
            for record in self.record.children
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def hash(self) -> str:
        return make_hash(self)

    @property
    def old_hash_mapping(self) -> Generator[tuple[str, str], None, None]:
        for study in self.studies:
            yield from (
                (f"{self.name}:{old_name}", f"{self}_{new_name}")
                for old_name, new_name in study.old_hash_mapping
            )

    @property
    def old_name_mapping(self) -> Generator[tuple[str, str], None, None]:
        for study in self.studies:
            yield from (
                (old_name, f"{self}_{new_name}")
                for old_name, new_name in study.old_name_mapping
            )

    @property
    def serieses(self) -> Generator[Series, None, None]:
        for study in self.studies:
            yield from (
                Series(f"{self}_{series.name}", series.data)
                for series in study.serieses
            )

    @property
    def series_names(self) -> Generator[tuple[str, DicomSeries], None, None]:
        for study in self.studies:
            yield from (
                (f"{self}_{name}", series)
                for name, series in study.series_names
            )
