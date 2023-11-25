import io
import pickle
from functools import singledispatch
from pathlib import Path
from typing import Any

from minio_path.path import MinioPath


@singledispatch
def pickle_dump(path: Any, obj: Any) -> None:
    ...


@pickle_dump.register
def _dump_s3(path: MinioPath, obj: Any) -> None:
    if path.exists():
        return
    buffer = io.BytesIO()
    pickle.dump(obj, buffer)
    path.write(io.BytesIO(buffer.getvalue()), buffer.tell())


@pickle_dump.register
def _dump_local(path: Path, obj: Any) -> None:
    if path.exists():
        return
    pickle.dump(obj, path)


@singledispatch
def pickle_load(path: Any) -> Any:
    ...


@pickle_load.register
def _load_s3(path: MinioPath) -> Any:
    return pickle.load(path.read())


@pickle_load.register
def _load_local(path: Path) -> Any:
    return pickle.load(path)
