import unittest

from path_case_normalizer import normalize_path, find_duplicates


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
        normalized, _ = normalize_path("Foo\\\\Bar.txt", case_sensitive_os=False)
        self.assertEqual(normalized, "foo/bar.txt")

    def test_backslash_normalized_case_sensitive(self):
        normalized, _ = normalize_path("Foo\\\\Bar.txt", case_sensitive_os=True)
        self.assertEqual(normalized, "Foo/Bar.txt")

    def test_empty_string(self):
        normalized, modified = normalize_path("", case_sensitive_os=False)
        self.assertEqual(normalized, "")
        self.assertFalse(modified)

    def test_type_error_on_non_string(self):
        with self.assertRaises(TypeError):
            normalize_path(123, case_sensitive_os=False)

    def test_mixed_separators(self):
        normalized, _ = normalize_path("Foo/Bar\\\\Baz", case_sensitive_os=False)
        self.assertEqual(normalized, "foo/bar/baz")

    def test_no_modification_when_already_normalized(self):
        # Path that is already lowercase with forward slashes should not
        # be reported as modified, even on case-insensitive systems.
        normalized, modified = normalize_path("a/b/c", case_sensitive_os=False)
        self.assertFalse(modified)


class TestFindDuplicates(unittest.TestCase):

    def test_basic_duplicates_case_insensitive(self):
        paths = ["Foo/Bar.txt", "foo/bar.txt", "baz/qux.txt"]
        groups = find_duplicates(paths, case_sensitive_os=False)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0], ["Foo/Bar.txt", "foo/bar.txt"])

    def test_no_duplicates_case_sensitive(self):
        paths = ["Foo/Bar.txt", "foo/bar.txt", "baz/qux.txt"]
        groups = find_duplicates(paths, case_sensitive_os=True)
        self.assertEqual(groups, [])

    def test_separator_variants_are_duplicates(self):
        paths = ["Foo/Bar.txt", "foo\\\\bar.txt"]
        groups = find_duplicates(paths, case_sensitive_os=False)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0], ["Foo/Bar.txt", "foo\\\\bar.txt"])

    def test_multiple_groups_preserve_order(self):
        paths = ["A/b", "a/B", "C/d", "c/D", "e/f"]
        groups = find_duplicates(paths, case_sensitive_os=False)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0], ["A/b", "a/B"])
        self.assertEqual(groups[1], ["C/d", "c/D"])

    def test_empty_input(self):
        groups = find_duplicates([], case_sensitive_os=False)
        self.assertEqual(groups, [])

    def test_single_path_no_duplicates(self):
        groups = find_duplicates(["only/one.txt"], case_sensitive_os=False)
        self.assertEqual(groups, [])

    def test_three_way_duplicate(self):
        paths = ["Foo.txt", "FOO.txt", "foo.txt"]
        groups = find_duplicates(paths, case_sensitive_os=False)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0], ["Foo.txt", "FOO.txt", "foo.txt"])

    def test_unique_paths_returned_empty(self):
        paths = ["a.txt", "b.txt", "c.txt"]
        groups = find_duplicates(paths, case_sensitive_os=False)
        self.assertEqual(groups, [])


if __name__ == "__main__":
    unittest.main()
