from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .compare import CompareBudget, compare_reports
from .overlap import compute_overlap
from .retrieval import score_retrieval

try:
    __version__ = version("toolkit-rag-quality-toolkit")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = [
    "CompareBudget",
    "__version__",
    "compare_reports",
    "compute_overlap",
    "score_retrieval",
]

