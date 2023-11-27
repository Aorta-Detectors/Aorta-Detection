import io
from functools import singledispatch
from pathlib import Path
from typing import Any

import torch as t

from minio_path.path import MinioPath


@singledispatch
def torch_load(path: Any) -> Any:
    ...


@torch_load.register
def _torch_load_s3(path: MinioPath) -> Any:
    return t.load(path.read())


@torch_load.register(str)
@torch_load.register(Path)
def _torch_load_local(path: Path) -> Any:
    return t.load(path)


@singledispatch
def torch_dump(path: Any, state: Any) -> None:
    ...


@torch_dump.register
def _torch_dump_s3(path: MinioPath, state: Any) -> None:
    if path.exists():
        return
    buffer = io.BytesIO()
    t.save(buffer, state)
    path.write(io.BytesIO(buffer.getvalue()), buffer.tell())


@torch_dump.register(str)
@torch_dump.register(Path)
def _torch_dump_local(path: Path, state: Any) -> None:
    t.save(path, state)
