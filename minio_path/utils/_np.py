import io
from functools import singledispatch
from pathlib import Path
from typing import Any

import numpy as np

from minio_path.path import MinioPath


@singledispatch
def numpy_dump(path: Any, array: np.ndarray) -> None:
    ...


@numpy_dump.register
def _numpy_dump_s3(path: MinioPath, array: np.ndarray) -> None:
    if path.exists():
        return
    buffer = io.BytesIO()
    np.save(buffer, array)
    path.write(io.BytesIO(buffer.getvalue()), buffer.tell())


@numpy_dump.register
def _numpy_dump_local(path: Path, array: np.ndarray) -> None:
    if path.exists():
        return
    np.save(path, array)


@singledispatch
def numpy_load(path: Any) -> Any:
    ...


@numpy_load.register
def _numpy_load_s3(path: MinioPath) -> np.ndarray:
    return np.load(path.read())


@numpy_load.register
def _numpy_load_local(path: Path) -> np.ndarray:
    return np.load(path)
