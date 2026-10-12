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

## Why

On case-insensitive filesystems (macOS default, Windows default), `Foo/Bar.txt` and `foo/bar.txt` point to the same file. If you are building a list of file paths from multiple sources, you can end up with duplicates that string comparison won't catch. This library lowercases paths and normalizes separators so such duplicates can be grouped.

The trade-off: lowercasing is lossy. On a case-sensitive filesystem (Linux default), `Foo.txt` and `foo.txt` are different files. The library auto-detects the host filesystem's sensitivity, but you should pass `case_sensitive_os` explicitly when processing paths from a filesystem other than your own.

## Edge cases

Backslashes are normalized to forward slashes, so `Foo\Bar` and `Foo/Bar` are treated as duplicates. This is correct for filesystem path comparison but means the library is not suitable for comparing arbitrary strings that happen to contain backslashes.

Auto-detection of filesystem sensitivity is a heuristic based on probing the root directory. If probing fails (permissions, unusual mounts), it assumes case-sensitive to avoid false duplicates. Pass `case_sensitive_os` explicitly when you know the answer.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

