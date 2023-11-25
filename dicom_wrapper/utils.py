from .cube import DicomCube
from .parser import PT, DicomParser


def dicom_find(path: PT):
    for sub_path in path.iterdir():
        if sub_path.name == "DICOMDIR":
            yield DicomCube(DicomParser(sub_path))
        if sub_path.is_dir() and path != sub_path:
            try:
                yield from dicom_find(sub_path)
            except Exception as exp:
                print(exp)
