"""Normalize path casing for case-insensitive filesystems.

The goal is to detect duplicate paths that differ only in letter casing,
which on case-insensitive filesystems (like macOS HFS+/APFS default, Windows
NTFS default) would point to the same file or directory.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Sequence

__all__ = [
    "normalize_path",
    "find_duplicates",
    "contains_duplicates",
    "canonical_path",
    "entries_are_case_sensitive",
]


def normalize_path(path: str, case_sensitive_os: bool | None = None) -> tuple[str, bool]:
    """Normalize a path's casing for duplicate detection.

    Returns a tuple of (normalized_path, was_modified).

    The normalization strategy depends on whether the filesystem is
    case-sensitive or case-insensitive:

    - On a case-insensitive filesystem, the path is lowercased so that
      paths differing only in case compare equal. This is the primary
      use case for this library.
    - On a case-sensitive filesystem, paths are returned unchanged because
      different casings refer to different files. Lowercasing would lose
      information and produce false duplicates.

    The ``case_sensitive_os`` parameter lets callers override the
    auto-detected behavior. This is essential for testing and for
    processing paths from a filesystem with different sensitivity than
    the host.

    Path separators are normalized to forward slashes so that ``Foo/Bar``
    and ``Foo\\Bar`` compare as duplicates, which they would be on any
    real filesystem.

    Raises TypeError if ``path`` is not a str.
    """
    if not isinstance(path, str):
        raise TypeError(f"path must be a string, got {type(path).__name__}")

    if case_sensitive_os is None:
        case_sensitive_os = _is_case_sensitive_os()

    # Normalize separators first so that casing normalization operates on
    # a consistent representation.
    normalized = re.sub(r"/+", "/", path.replace("\\", "/"))

    if not case_sensitive_os:
        normalized = normalized.lower()

    was_modified = normalized != path
    return normalized, was_modified


def canonical_path(path: str, case_sensitive_os: bool | None = None) -> str:
    """Return the canonical (deduplicated) form of a single path.

    This is the normalized form that ``find_duplicates`` groups by. Useful
    when you want a stable "first surviving" representation to keep while
    discarding the rest of a duplicate group::

        keep = canonical_path(sys.argv[1])
    """
    normalized, _ = normalize_path(path, case_sensitive_os=case_sensitive_os)
    return normalized


def find_duplicates(paths: Iterable[str], case_sensitive_os: bool | None = None) -> list[list[str]]:
    """Find paths that are duplicates under case-insensitive comparison.

    Returns a list of groups, where each group is a list of original paths
    that normalize to the same value. Only groups with two or more paths
    are included.

    The order of groups and the order of paths within a group follows the
    order of the input iterable.

    If ``case_sensitive_os`` is True, no paths are considered duplicates
    (since different casings refer to different files). This parameter is
    primarily useful for testing and for processing paths from a
    filesystem with different sensitivity than the host.
    """
    if case_sensitive_os is None:
        case_sensitive_os = _is_case_sensitive_os()

    # Use a dict to group paths by their normalized form. Each value is a
    # list of original paths in first-seen order.
    groups: dict[str, list[str]] = {}
    order: list[str] = []  # preserves first-seen order of normalized keys

    for path in paths:
        normalized, _ = normalize_path(path, case_sensitive_os=case_sensitive_os)
        if normalized not in groups:
            groups[normalized] = []
            order.append(normalized)
        groups[normalized].append(path)

    return [groups[key] for key in order if len(groups[key]) >= 2]


def contains_duplicates(paths: Iterable[str], case_sensitive_os: bool | None = None) -> bool:
    """Return True if *any* duplicate group exists.

    Short-circuits on the first duplicate pair found, so it is cheaper than
    building every group when you only need a yes/no answer.
    """
    if case_sensitive_os is None:
        case_sensitive_os = _is_case_sensitive_os()

    seen: set[str] = set()
    for path in paths:
        normalized, _ = normalize_path(path, case_sensitive_os=case_sensitive_os)
        if normalized in seen:
            return True
        seen.add(normalized)
    return False


def entries_are_case_sensitive(entries: Sequence[str]) -> bool:
    """Pure helper: decide case-sensitivity from a list of directory entries.

    A filesystem is case-sensitive iff two *distinct* entries differ only
    by letter casing (``README`` and ``readme`` both present). On a
    case-insensitive-but-case-preserving filesystem (macOS APFS default,
    Windows NTFS default) the directory lists only the canonical casing, so
    no case-variant pair appears -- even when entries contain uppercase
    letters.

    Extracted so the detection logic can be unit-tested without touching a
    real filesystem.
    """
    seen_lower: dict[str, str] = {}
    for entry in entries:
        low = entry.lower()
        if low in seen_lower and seen_lower[low] != entry:
            # Two distinct entries differ only in case -> case-sensitive.
            return True
        seen_lower[low] = entry
    return False


def _is_case_sensitive_os() -> bool:
    """Detect whether the host filesystem is case-sensitive.

    We probe by checking if the root directory treats 'tmp' and 'TMP' as
    the same entry. This is a heuristic: it reflects the sensitivity of
    the root volume, which is the common case. For more exotic setups
    (multiple volumes with different sensitivity), callers should pass
    ``case_sensitive_os`` explicitly.
    """
    # On Windows, filesystems are case-insensitive by default.
    if os.name == "nt":
        return False

    # On POSIX systems, probe the actual filesystem behavior.
    root = os.path.abspath(os.sep)
    try:
        entries = os.listdir(root)
    except OSError:
        # If we can't list the root, assume case-sensitive (the POSIX
        # default). This is a safe fallback because it avoids false
        # duplicate detection.
        return True

    # A genuine case-variant pair (two distinct entries differing only in
    # case) proves the filesystem is case-sensitive. We check against
    # DISTINCT entries, not a set of lowercased names -- a single uppercase
    # entry is NOT evidence of case-sensitivity on macOS/Windows.
    if entries_are_case_sensitive(entries):
        return True

    # No case-variant pairs found. This usually means case-insensitive,
    # but could also mean a case-sensitive filesystem that simply has no
    # such pairs. We check by testing if a known directory exists in both
    # casings.
    #
    # Use /tmp or /etc as a probe: on case-insensitive systems, both
    # 'tmp' and 'TMP' would resolve to the same directory.
    for probe in ("tmp", "etc", "var", "home"):
        probe_path = os.path.join(root, probe)
        upper_path = os.path.join(root, probe.upper())
        try:
            probe_stat = os.stat(probe_path)
            upper_stat = os.stat(upper_path)
            # Same inode => same file => case-insensitive
            if probe_stat.st_ino == upper_stat.st_ino and probe_stat.st_dev == upper_stat.st_dev:
                return False
            # Different inodes for what would be the same name on a
            # case-insensitive system => case-sensitive.
            return True
        except OSError:
            continue

    # Could not determine; assume case-sensitive to avoid false duplicates.
    return True