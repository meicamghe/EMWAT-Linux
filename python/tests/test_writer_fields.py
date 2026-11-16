import unittest

from emwat_linux.writer_fields import (
    WriterFieldRefreshError,
    refresh_writer_text_fields,
)


class FakeTextFields:
    def __init__(self):
        self.refresh_count = 0

    def refresh(self):
        self.refresh_count += 1


class FakeDocument:
    def __init__(self):
        self.fields = FakeTextFields()

    def getTextFields(self):
        return self.fields


class BrokenDocument:
    def getTextFields(self):
        raise RuntimeError("UNO unavailable")


class WriterFieldRefreshTests(unittest.TestCase):
    def test_refreshes_text_fields_once(self):
        document = FakeDocument()
        refresh_writer_text_fields(document)
        self.assertEqual(document.fields.refresh_count, 1)

    def test_wraps_uno_refresh_errors(self):
        with self.assertRaises(WriterFieldRefreshError):
            refresh_writer_text_fields(BrokenDocument())


if __name__ == "__main__":
    unittest.main()
