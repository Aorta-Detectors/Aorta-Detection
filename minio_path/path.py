import io
from typing import Generator, Self

from minio import Minio, S3Error

from .config import MinioConfig


class MinioPath:
    sep = "/"

    def __init__(self, minio: Minio, path="", parent: Self | None = None):
        self.minio = minio
        self._path = path
        self.parent = parent

    @property
    def path(self) -> str:
        return self._path

    @path.setter
    def path(self, new_path: str):
        if (
            new_path.startswith(self.sep)
            and self._path.endswith(self.sep)
            and new_path == self.sep
        ):
            self.path
        elif new_path.startswith(self.sep) or self._path.endswith(self.sep):
            self._path += new_path
        else:
            self._path += f"{self.sep}{new_path}"

    @property
    def bucket(self) -> str | None:
        if self.sep not in self.path:
            return None
        _, bucket, *_ = self._path.split(self.sep, 2)
        return bucket

    @property
    def objectname(self) -> str | None:
        if self.sep not in self.path.strip(self.sep):
            return ""
        _, _, path = self._path.split(self.sep, 2)
        return path

    @property
    def name(self) -> str:
        name = self._path.split("/")[-1]
        return name.strip("/")

    @classmethod
    def fromauth(
        cls, host: str, access_key: str, secret_key: str, **kwargs
    ) -> Self:
        return MinioPath(
            Minio(host, access_key=access_key, secret_key=secret_key, **kwargs)
        )

    @classmethod
    def fromconfig(cls, config: MinioConfig) -> Self:
        return cls.fromauth(**config.dict())

    @classmethod
    def frompath(cls, current_path: Self, new_path: str) -> Self:
        new_minio_path = cls(
            minio=current_path.minio,
            path=current_path.path,
            parent=current_path,
        )
        new_minio_path.parent.path = cls.sep
        new_minio_path.path = new_path
        return new_minio_path

    def __truediv__(self, path: str) -> Self:
        return MinioPath.frompath(self, path)

    def joinpath(self, *paths: str):
        if len(paths) <= 1:
            return self / paths[0]
        if len(paths[0]) == 0:
            return self.joinpath(*paths[1:])
        return (self / f"{paths[0].rstrip(self.sep)}{self.sep}").joinpath(
            *paths[1:]
        )

    def __str__(self) -> str:
        return self._path

    def __repr__(self) -> str:
        return self._path

    def __eq__(self, other: Self) -> bool:
        return self._path == other._path

    def __neq__(self, other: Self) -> bool:
        return self._path != other._path

    def iterdir(self) -> Generator[Self, None, None]:
        for minio_object in self.minio.list_objects(
            self.bucket, prefix=self.objectname
        ):
            yield self / minio_object._object_name[len(self.objectname) :]

    def is_dir(self) -> bool:
        """Get whether this key is a directory."""
        return self.objectname.endswith("/")

    def exists(self) -> bool:
        try:
            result = self.minio.stat_object(self.bucket, self.objectname)
            return result is not None
        except S3Error:
            return False

    def read(self) -> io.BytesIO:
        response = self.minio.get_object(self.bucket, self.objectname)
        return io.BytesIO(response.read())

    def write(self, open_file: io.BytesIO, length: int):
        self.minio.put_object(
            self.bucket,
            self.objectname,
            open_file,
            length,
        )

    def open(self, mode="r") -> Self:
        return self
