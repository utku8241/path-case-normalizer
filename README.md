# Path Case Normalizer

Normalizes path casing for case-insensitive filesystems so you can detect duplicate paths that differ only in letter case.

## Usage

```python
from path_case_normalizer import normalize_path, find_duplicates

normalized, was_modified = normalize_path("Foo/Bar.txt", case_sensitive_os=False)
# normalized == "foo/bar.txt", was_modified == True

dups = find_duplicates(["Foo/Bar.txt", "foo/bar.txt", "baz/qux.txt"], case_sensitive_os=False)
# dups == [["Foo/Bar.txt", "foo/bar.txt"]]
```

### Convenience helpers

```python
from path_case_normalizer import contains_duplicates, canonical_path

# Fast yes/no check (short-circuits on the first duplicate pair).
contains_duplicates(["a.txt", "A.txt", "b.txt"], case_sensitive_os=False)   # True

# The form find_duplicates groups by — keep this, discard the rest.
canonical_path("Foo/Bar.txt", case_sensitive_os=False)                      # "foo/bar.txt"

# Pure, dependency-free case-sensitivity check over arbitrary entries
# (testable without touching the real filesystem).
from path_case_normalizer import entries_are_case_sensitive
entries_are_case_sensitive(["README", "readme"])     # True  (case-variant pair)
entries_are_case_sensitive(["Applications", "System"])  # False (no case-variant pair)
```

### Command line

```
$ printf 'Foo/Bar.txt\nfoo/bar.txt\nbaz/qux.txt\n' | path-case-normalizer --numbered
[1]
  Foo/Bar.txt
  foo/bar.txt

1 duplicate group(s) found.
```

Reads one path per line from the given files (or stdin when none are given),
skips blank lines and `#` comments, and prints any duplicate groups.

Exit codes: `0` no duplicates · `1` at least one duplicate group · `2` usage/IO
error. Use it as a guard in scripts:

```bash
if printf '%s\n' "${paths[@]}" | path-case-normalizer --case-sensitive > /dev/null; then
  echo "no duplicate paths"
fi
```

Flags:

| Flag | Description |
|---|---|
| `--case-sensitive` | Treat the filesystem as case-sensitive (disable lowercasing) |
| `--numbered` | Prepend each group with its 1-based group number |

## Why

On case-insensitive filesystems (macOS default, Windows default), `Foo/Bar.txt` and `foo/bar.txt` point to the same file. If you are building a list of file paths from multiple sources, you can end up with duplicates that string comparison won't catch. This library lowercases paths and normalizes separators so such duplicates can be grouped.

The trade-off: lowercasing is lossy. On a case-sensitive filesystem (Linux default), `Foo.txt` and `foo.txt` are different files. The library auto-detects the host filesystem's sensitivity, but you should pass `case_sensitive_os` explicitly when processing paths from a filesystem other than your own.

## Edge cases

Backslashes are normalized to forward slashes, so `Foo\Bar` and `Foo/Bar` are treated as duplicates. This is correct for filesystem path comparison but means the library is not suitable for comparing arbitrary strings that happen to contain backslashes. Consecutive separators (`a//b`) collapse to a single separator.

Auto-detection of filesystem sensitivity is a heuristic. A filesystem is judged case-sensitive only when it shows a *pair* of distinct entries that differ purely by letter casing. A single uppercase entry (like `Applications` on macOS APFS) is **not** evidence of case-sensitivity — that is exactly what happens on case-insensitive-but-case-preserving filesystems, and detecting them as sensitive would silently defeat the library's purpose. As a fallback, probing compares the inode of `/tmp` against `/TMP`. If probing fails (permissions, unusual mounts), it assumes case-sensitive to avoid false duplicates. Pass `case_sensitive_os` explicitly when you know the answer.

## Performance

`normalize_path` does a single regex substitution plus (on case-insensitive filesystems) a `.lower()` pass, so it is O(len(path)) with no per-path allocation beyond the result string. `find_duplicates` and `contains_duplicates` are O(n) in the number of paths using a hash map; `contains_duplicates` returns as soon as a duplicate pair is found.

## License

MIT