from ._condirtional_import import import_if_install as __import_if_install
from .pickle import pickle_dump, pickle_load
from .read import read_file, recursive_read_files

if __import_if_install("numpy"):
    from ._np import numpy_dump, numpy_load
if __import_if_install("torch"):
    from ._t import torch_dump, torch_load

__all__ = [
    "pickle_dump",
    "pickle_load",
    "read_file",
    "recursive_read_files",
    "numpy_dump",
    "numpy_load",
    "torch_dump",
    "torch_load",
]
