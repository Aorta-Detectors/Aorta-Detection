import hashlib
from pathlib import Path
from typing import Any, Iterable

from minio_path import MinioPath
from minio_path.utils import read_file
from pydicom.dataset import FileDataset
from pydicom.filereader import dcmread

PT = Path | MinioPath


def _get_shortest_path(paths: Iterable[PT], parent_path: PT) -> PT:
    return min(
        [path for path in paths if path.is_dir() and path != parent_path],
        key=lambda x: len(x.name),
    )


def make_hash(data: Any) -> str:
    return hashlib.md5(str(data).encode()).hexdigest()


class DicomParser:
    def __init__(self, path: PT):
        if path.name == "DICOMDIR":
            self.slice_path = _get_shortest_path(path.parent.iterdir(), path.parent)
        else:
            self.slice_path = _get_shortest_path(path.iterdir(), path)
        self.path = path

    def read(self) -> FileDataset:
        with dcmread(read_file(self.path), force=True) as dicom:
            return dicom
