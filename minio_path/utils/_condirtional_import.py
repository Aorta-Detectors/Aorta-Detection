import importlib
import logging
from types import ModuleType

logger = logging.getLogger(__name__)


def import_if_install(mod_name: str) -> ModuleType | None:
    try:
        importlib.import_module(mod_name)
    except ModuleNotFoundError:
        logging.warning(
            f"MinioPath {mod_name} utils disabled."
            f"Please install {mod_name}."
            f"Write `pip install {mod_name}`."
        )
        return False

    return True
