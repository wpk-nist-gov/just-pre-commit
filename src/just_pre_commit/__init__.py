<<<<<<< before updating
=======
"""
Top level API (:mod:`just_pre_commit`)
======================================================
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

from .core import example_function

try:  # ruff:ignore[non-empty-init-module]
    __version__ = _version("just-pre-commit")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "999"


__author__ = """William P. Krekelberg"""


__all__ = [
    "__version__",
    "example_function",
]
>>>>>>> after updating
