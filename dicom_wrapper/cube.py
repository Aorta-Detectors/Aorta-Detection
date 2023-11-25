import io
from typing import Generator

from minio_path import MinioPath
from minio_path.utils import read_file, recursive_read_files

from .parser import DicomParser, make_hash
from .patient import DicomPatient
from .series import DicomSeries, Series


class DicomCube:
    def __init__(self, parser: DicomParser):
        self.path = parser.path
        self.slice_path = parser.slice_path
        self.dicom = parser.read()
        self.patient_records = [
            DicomPatient(record, self.path, self.slice_path)
            for record in self.dicom.patient_records
        ]

    def __str__(self) -> str:
        return str(self.path)

    @property
    def hash(self) -> str:
        return make_hash(self.dicom)

    @property
    def old_hash_mapping(self) -> Generator[tuple[str, str], None, None]:
        for patient in self.patient_records:
            yield from (
                (make_hash(old_name), make_hash(new_name))
                for old_name, new_name in patient.old_hash_mapping
            )

    @property
    def old_name_mapping(self) -> Generator[tuple[str, str], None, None]:
        for patient in self.patient_records:
            yield from (
                (old_name, make_hash(new_name))
                for old_name, new_name in patient.old_name_mapping
            )

    @property
    def serieses(self) -> Generator[Series, None, None]:
        for patient in self.patient_records:
            yield from (
                Series(make_hash(series.name), series.data)
                for series in patient.serieses
            )

    @property
    def serieses_name(self) -> Generator[tuple[str, DicomSeries], None, None]:
        for patient in self.patient_records:
            yield from (
                (make_hash(name), series) for name, series in patient.series_names
            )

    def upload(self, s3path: MinioPath):
        dicom = read_file(self.path)
        data = dicom.read()
        (s3path / self.hash / "DICOMDIR").write(io.BytesIO(data), len(data))
        for slice_file, slice_io_data in recursive_read_files(self.slice_path):
            slice_name = str(slice_file).replace(str(self.path.parent), "")
            slice_data = slice_io_data.read()
            (s3path / self.hash / slice_name).write(
                io.BytesIO(slice_data), len(slice_data)
            )

        return s3path / self.hash / "DICOMDIR"
