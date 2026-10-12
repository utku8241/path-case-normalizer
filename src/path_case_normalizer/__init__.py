from .core import (
    canonical_path,
    contains_duplicates,
    entries_are_case_sensitive,
    find_duplicates,
    normalize_path,
)

__all__ = [
    "normalize_path",
    "find_duplicates",
    "contains_duplicates",
    "canonical_path",
    "entries_are_case_sensitive",
]

__version__ = "0.1.3"