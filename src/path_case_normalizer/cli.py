"""Command-line interface for path-case-normalizer.

Reads paths one-per-line from stdin (or the given files/args) and prints
any duplicate groups found under case-insensitive comparison. Exits 0 when
no duplicates are found, 1 when at least one duplicate group exists, and 2
on usage errors.
"""

from __future__ import annotations

import argparse
import sys
from typing import TextIO

from .core import find_duplicates


def _read_paths(stream: TextIO) -> list[str]:
    """Read non-empty, non-comment lines from a stream."""
    out: list[str] = []
    for raw in stream:
        line = raw.rstrip("\n").rstrip("\r")
        if line and not line.startswith("#"):
            out.append(line)
    return out


def _print_groups(groups: list[list[str]], show_numbers: bool) -> None:
    for i, group in enumerate(groups, start=1):
        if show_numbers:
            print(f"[{i}]")
        for path in group:
            print(f"  {path}")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="path-case-normalizer",
        description="Detect duplicate paths that differ only by letter casing. "
        "Reads paths one-per-line from files, or stdin when none are given.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help="Files to read paths from (one path per line). Defaults to stdin.",
    )
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Treat the filesystem as case-sensitive (disables lowercasing).",
    )
    parser.add_argument(
        "--numbered",
        action="store_true",
        help="Prepend each group with its 1-based group number.",
    )
    args = parser.parse_args(argv)

    case_sensitive = args.case_sensitive
    paths: list[str] = []

    if args.files:
        for fname in args.files:
            try:
                with open(fname, encoding="utf-8") as fh:
                    paths.extend(_read_paths(fh))
            except OSError as exc:
                print(f"path-case-normalizer: error: {fname}: {exc.strerror or exc}", file=sys.stderr)
                return 2
    else:
        paths = _read_paths(sys.stdin)

    groups = find_duplicates(paths, case_sensitive_os=case_sensitive)

    if groups:
        _print_groups(groups, args.numbered)
        print(f"{len(groups)} duplicate group(s) found.", file=sys.stderr)
        # 1 = at least one duplicate group. This makes the tool easy to use
        # as a non-zero-exit guard in scripts.
        return 1

    print("No duplicate paths found.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())