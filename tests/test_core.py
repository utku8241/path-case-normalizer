"""Tests for path_case_normalizer.

Written as ``unittest.TestCase`` classes so they run under the repo's CI
(``python -m unittest discover -s tests -v``) with no third-party
dependencies installed. Also runnable under ``pytest``.
"""

import io
import unittest
from contextlib import redirect_stdout

from path_case_normalizer import (
    canonical_path,
    contains_duplicates,
    entries_are_case_sensitive,
    find_duplicates,
    normalize_path,
)
from path_case_normalizer.cli import _read_paths, main


def _run_cli(argv, stdin_lines):
    """Run the CLI with synthetic stdin/argv; returns (exit_code, stdout)."""
    from path_case_normalizer import cli as cli_mod

    out = io.StringIO()
    orig_stdin = cli_mod.sys.stdin
    cli_mod.sys.stdin = io.StringIO("".join(stdin_lines))
    try:
        with redirect_stdout(out):
            rc = main(argv)
    finally:
        cli_mod.sys.stdin = orig_stdin
    return rc, out.getvalue()


class TestNormalizePath(unittest.TestCase):

    def test_lowercase_on_case_insensitive(self):
        normalized, modified = normalize_path("Foo/Bar.txt", case_sensitive_os=False)
        self.assertEqual(normalized, "foo/bar.txt")
        self.assertTrue(modified)

    def test_no_change_on_case_sensitive(self):
        normalized, modified = normalize_path("Foo/Bar.txt", case_sensitive_os=True)
        self.assertEqual(normalized, "Foo/Bar.txt")
        self.assertFalse(modified)

    def test_already_lowercase_no_modification(self):
        normalized, modified = normalize_path("foo/bar.txt", case_sensitive_os=False)
        self.assertEqual(normalized, "foo/bar.txt")
        self.assertFalse(modified)

    def test_backslash_normalized_to_forward_slash(self):
        normalized, _ = normalize_path("Foo\\Bar.txt", case_sensitive_os=False)
        self.assertEqual(normalized, "foo/bar.txt")

    def test_backslash_normalized_case_sensitive(self):
        normalized, _ = normalize_path("Foo\\Bar.txt", case_sensitive_os=True)
        self.assertEqual(normalized, "Foo/Bar.txt")

    def test_empty_string(self):
        normalized, modified = normalize_path("", case_sensitive_os=False)
        self.assertEqual(normalized, "")
        self.assertFalse(modified)

    def test_type_error_on_non_string(self):
        with self.assertRaises(TypeError):
            normalize_path(123, case_sensitive_os=False)

    def test_mixed_separators(self):
        normalized, _ = normalize_path("Foo/Bar\\Baz", case_sensitive_os=False)
        self.assertEqual(normalized, "foo/bar/baz")

    def test_consecutive_separators_collapse(self):
        normalized, _ = normalize_path("a//b///c", case_sensitive_os=False)
        self.assertEqual(normalized, "a/b/c")

    def test_no_modification_when_already_normalized(self):
        normalized, modified = normalize_path("a/b/c", case_sensitive_os=False)
        self.assertFalse(modified)

    def test_unicode_lowercase(self):
        normalized, modified = normalize_path("ZOLC/ZDZBLOWA.TXT", case_sensitive_os=False)
        self.assertEqual(normalized, "zolc/zdzblowa.txt")
        self.assertTrue(modified)

    def test_unicode_upper_to_lower(self):
        normalized, modified = normalize_path("\u017b\u00d3\u0141\u0106/\u0179.DIR", case_sensitive_os=False)
        self.assertEqual(normalized, "\u017c\u00f3\u0142\u0107/\u017a.dir")
        self.assertTrue(modified)

    def test_canonical_path_matches_normalized(self):
        self.assertEqual(canonical_path("Foo/Bar.txt", case_sensitive_os=False), "foo/bar.txt")


class TestFindDuplicates(unittest.TestCase):

    def test_basic_duplicates_case_insensitive(self):
        groups = find_duplicates(["Foo/Bar.txt", "foo/bar.txt", "baz/qux.txt"],
                                 case_sensitive_os=False)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0], ["Foo/Bar.txt", "foo/bar.txt"])

    def test_no_duplicates_case_sensitive(self):
        self.assertEqual(find_duplicates(["Foo/Bar.txt", "foo/bar.txt"],
                                         case_sensitive_os=True), [])

    def test_separator_variants_are_duplicates(self):
        groups = find_duplicates(["Foo/Bar.txt", "foo\\bar.txt"], case_sensitive_os=False)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0], ["Foo/Bar.txt", "foo\\bar.txt"])

    def test_multiple_groups_preserve_order(self):
        paths = ["A/b", "a/B", "C/d", "c/D", "e/f"]
        groups = find_duplicates(paths, case_sensitive_os=False)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0], ["A/b", "a/B"])
        self.assertEqual(groups[1], ["C/d", "c/D"])

    def test_empty_input(self):
        self.assertEqual(find_duplicates([], case_sensitive_os=False), [])

    def test_single_path_no_duplicates(self):
        self.assertEqual(find_duplicates(["only/one.txt"], case_sensitive_os=False), [])

    def test_three_way_duplicate(self):
        groups = find_duplicates(["Foo.txt", "FOO.txt", "foo.txt"], case_sensitive_os=False)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0], ["Foo.txt", "FOO.txt", "foo.txt"])

    def test_unique_paths_returned_empty(self):
        self.assertEqual(find_duplicates(["a.txt", "b.txt", "c.txt"], case_sensitive_os=False), [])

    def test_accepts_generator_input(self):
        gen = (p for p in ["a.txt", "A.txt"])
        self.assertEqual(len(find_duplicates(gen, case_sensitive_os=False)), 1)


class TestContainsDuplicates(unittest.TestCase):

    def test_true(self):
        self.assertTrue(contains_duplicates(
            ["foo.txt", "bar.txt", "FOO.txt"], case_sensitive_os=False))

    def test_false(self):
        self.assertFalse(contains_duplicates(["a.txt", "b.txt"], case_sensitive_os=False))

    def test_empty(self):
        self.assertFalse(contains_duplicates([], case_sensitive_os=False))

    def test_case_sensitive(self):
        self.assertFalse(contains_duplicates(["Foo.txt", "foo.txt"], case_sensitive_os=True))


class TestEntriesAreCaseSensitive(unittest.TestCase):
    """Unit tests for the extracted detection logic — the real bug fix."""

    def test_case_variant_pair_is_sensitive(self):
        self.assertTrue(entries_are_case_sensitive(["README", "readme"]))
        self.assertTrue(entries_are_case_sensitive(["Makefile", "makefile", "README"]))

    def test_uppercase_only_entries_are_insensitive(self):
        # macOS APFS is case-insensitive but preserves the on-disk casing;
        # a single uppercase entry is NOT evidence of case-sensitivity.
        self.assertFalse(entries_are_case_sensitive(
            ["Applications", "Library", "System", "Users"]))

    def test_all_lowercase_is_insensitive(self):
        self.assertFalse(entries_are_case_sensitive(["etc", "var", "home", "tmp"]))

    def test_empty_is_insensitive(self):
        self.assertFalse(entries_are_case_sensitive([]))

    def test_mixed_case_preserving_pair_detected(self):
        self.assertTrue(entries_are_case_sensitive(["Foo", "Foo.txt", "foo"]))


class TestCli(unittest.TestCase):

    def test_finds_duplicates_from_stdin(self):
        rc, out = _run_cli([], ["Foo.txt\n", "foo.txt\n"])
        self.assertEqual(rc, 1)
        self.assertIn("Foo.txt", out)
        self.assertIn("foo.txt", out)

    def test_no_duplicates_exit_0(self):
        rc, out = _run_cli([], ["a.txt\n", "b.txt\n"])
        self.assertEqual(rc, 0)

    def test_case_sensitive_flag_disables_lowercasing(self):
        rc, _ = _run_cli(["--case-sensitive"], ["Foo.txt\n", "foo.txt\n"])
        self.assertEqual(rc, 0)

    def test_skips_blank_and_comment_lines(self):
        rc, _ = _run_cli([], ["Foo.txt\n", "# comment\n", "\n", "foo.txt\n"])
        self.assertEqual(rc, 1)

    def test_numbered_group_format(self):
        rc, out = _run_cli(["--numbered"], ["A.txt\n", "a.txt\n"])
        self.assertEqual(rc, 1)
        self.assertIn("[1]", out)

    def test_missing_file_exit_2(self):
        rc, _ = _run_cli(["/no/such/file_xyz.txt"], [])
        self.assertEqual(rc, 2)

    def test_duplicate_in_file_source(self):
        # Paths from a file (not stdin) still get grouped.
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("Alpha.txt\nalpha.txt\n")
            fname = fh.name
        try:
            rc, out = _run_cli([fname], [])
            self.assertEqual(rc, 1)
            self.assertIn("Alpha.txt", out)
            self.assertIn("alpha.txt", out)
        finally:
            import os
            os.unlink(fname)

    def test_read_paths_filters_blank_and_comments(self):
        stream = io.StringIO("a.txt\n\n# note\nb.txt\n")
        self.assertEqual(_read_paths(stream), ["a.txt", "b.txt"])


class TestHostDetectionSmoke(unittest.TestCase):

    def test_is_case_sensitive_os_returns_bool(self):
        from path_case_normalizer.core import _is_case_sensitive_os
        self.assertIsInstance(_is_case_sensitive_os(), bool)


if __name__ == "__main__":
    unittest.main()