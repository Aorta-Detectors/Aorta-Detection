import io
from functools import singledispatch
from pathlib import Path
from typing import Any, Generator

from minio_path.path import MinioPath


def recursive_read_files(
    path: MinioPath | Path,
) -> Generator[tuple[MinioPath | Path, io.BytesIO], None, None]:
    for subpath in path.iterdir():
        if subpath.is_dir() and subpath != path:
            yield from recursive_read_files(subpath)
        else:
            yield subpath, read_file(subpath)


@singledispatch
def read_file(path: Any) -> io.BytesIO:
    return io.BytesIO("")


@read_file.register
def _s3_read(path: MinioPath) -> io.BytesIO:
    return path.read()


@read_file.register
def _local_read(path: Path) -> io.BytesIO:
    return path.open("rb")
