import os
import unittest

from tests.test_notes_add_list import NotesCliBase, run_cli

BAD_FILES = {
    "notes_int": b'{"notes": 5}',
    "notes_null": b'{"notes": null}',
    "notes_missing": b"{}",
    "top_level_list": b"[]",
    "entry_not_object": b'{"notes": [1]}',
    "missing_id": b'{"notes": [{"text": "a"}]}',
    "missing_text": b'{"notes": [{"id": 1}]}',
    "id_str": b'{"notes": [{"id": "1", "text": "a"}]}',
    "id_bool": b'{"notes": [{"id": true, "text": "a"}]}',
    "id_float": b'{"notes": [{"id": 1.5, "text": "a"}]}',
    "text_int": b'{"notes": [{"id": 1, "text": 7}]}',
    "duplicate_ids": b'{"notes": [{"id": 1, "text": "a"}, {"id": 1, "text": "b"}]}',
    "invalid_json": b"{not json",
    "invalid_utf8": b'{"notes": [{"id": 1, "text": "\xff"}]}',
}


class MalformedFileTest(NotesCliBase):
    def assert_unreadable(self, argv, before):
        code, out, err = run_cli(*argv)
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("notes: error: cannot read"), err)
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertEqual(self.read_bytes(), before)

    def test_list_and_add_reject_bad_shapes(self):
        for name, data in BAD_FILES.items():
            with open(self.path, "wb") as f:
                f.write(data)
            for argv in (("notes", "list"), ("notes", "add", "x")):
                with self.subTest(case=name, argv=argv):
                    self.assert_unreadable(argv, data)

    def test_directory_path_is_unreadable(self):
        os.mkdir(self.path)
        for argv in (("notes", "list"), ("notes", "add", "x")):
            with self.subTest(argv=argv):
                code, _, err = run_cli(*argv)
                self.assertEqual(code, 2)
                self.assertTrue(err.startswith("notes: error: cannot read"), err)
                self.assertEqual(len(err.splitlines()), 1, err)
                self.assertEqual(os.listdir(self.path), [])


class StillValidTest(NotesCliBase):
    def test_file_written_by_add_still_loads(self):
        self.assertEqual(run_cli("notes", "add", "one")[0], 0)
        self.assertEqual(run_cli("notes", "add", "two")[0], 0)
        code, out, err = run_cli("notes", "list")
        self.assertEqual((code, out, err), (0, "1\tone\n2\ttwo\n", ""))

    def test_zero_byte_and_blank_file_mean_no_notes(self):
        for data in (b"", b"  \n"):
            with open(self.path, "wb") as f:
                f.write(data)
            with self.subTest(data=data):
                self.assertEqual(run_cli("notes", "list"), (0, "", ""))

    def test_empty_notes_list_is_valid(self):
        with open(self.path, "wb") as f:
            f.write(b'{"notes": []}')
        self.assertEqual(run_cli("notes", "list"), (0, "", ""))
        self.assertEqual(run_cli("notes", "add", "a")[1], "added 1\n")

    def test_extra_keys_are_tolerated(self):
        with open(self.path, "wb") as f:
            f.write(b'{"notes": [{"id": 3, "text": "a", "tag": "x"}], "v": 1}')
        self.assertEqual(run_cli("notes", "add", "b")[1], "added 4\n")


if __name__ == "__main__":
    unittest.main()
