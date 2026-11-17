import tempfile
import unittest
from threading import Event, Lock
from pathlib import Path

from emwat_linux.libreoffice_adapter import (
    _CFB_SIGNATURE,
    _DocumentCloseListener,
    _ModifyListener,
    _file_url,
    _source_extension,
    _stop_process,
)


class FakeProperty:
    def __init__(self):
        self.Name = ""
        self.Value = None


class FakeUno:
    @staticmethod
    def createUnoStruct(_name):
        return FakeProperty()


def fake_snapshot_properties():
    filter_name = FakeProperty()
    filter_name.Name = "FilterName"
    filter_name.Value = "MS Word 97"
    overwrite = FakeProperty()
    overwrite.Name = "Overwrite"
    overwrite.Value = True
    return (filter_name, overwrite)


class FakeDocument:
    def __init__(self, *, fail=False):
        self.calls = []
        self.fail = fail

    def storeToURL(self, url, properties):
        if self.fail:
            raise RuntimeError("synthetic export error")
        self.calls.append((url, [(p.Name, p.Value) for p in properties]))


class FakeProcess:
    def __init__(self):
        self.returncode = None
        self.terminated = False
        self.killed = False
        self.wait_calls = []

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        if not self.killed:
            import subprocess
            raise subprocess.TimeoutExpired("soffice", timeout)
        self.returncode = -9
        return self.returncode


class LibreOfficeAdapterUnitTests(unittest.TestCase):
    def test_stop_process_reaps_after_kill(self):
        process = FakeProcess()
        _stop_process(process, terminate_timeout=1, kill_timeout=2)
        self.assertTrue(process.terminated)
        self.assertTrue(process.killed)
        self.assertEqual(process.wait_calls, [1, 2])

    def test_stop_process_does_not_touch_exited_process(self):
        process = FakeProcess()
        process.returncode = 0
        _stop_process(process, terminate_timeout=1, kill_timeout=2)
        self.assertFalse(process.terminated)
        self.assertFalse(process.killed)
        self.assertEqual(process.wait_calls, [])

    def test_detects_legacy_word_compound_file(self):
        self.assertEqual(_source_extension(_CFB_SIGNATURE + b"payload"), ".doc")

    def test_detects_docx_zip_container(self):
        self.assertEqual(_source_extension(bytes.fromhex("504b0304") + b"payload"), ".docx")

    def test_rejects_unknown_document_container(self):
        with self.assertRaisesRegex(ValueError, "unsupported_word_document_container"):
            _source_extension(b"not-a-word-document")

    def test_file_url_is_absolute_and_escaped(self):
        with tempfile.TemporaryDirectory(prefix="emwat space ") as directory:
            path = Path(directory) / "document.doc"
            url = _file_url(path)
            self.assertTrue(url.startswith("file://"))
            self.assertIn("emwat%20space", url)

    def test_close_listener_snapshots_word_97_before_close(self):
        document = FakeDocument()
        closed = []
        listener = _DocumentCloseListener(
            document,
            "file:///tmp/final.doc",
            lambda: closed.append(True),
            fake_snapshot_properties(),
            Lock(),
            Event(),
        )
        listener.queryClosing(object(), False)
        self.assertTrue(listener.snapshot_ready.is_set())
        self.assertIsNone(listener.snapshot_error)
        self.assertEqual(
            document.calls,
            [("file:///tmp/final.doc", [("FilterName", "MS Word 97"), ("Overwrite", True)])],
        )
        listener.notifyClosed(object())
        self.assertEqual(closed, [True])

    def test_close_listener_retains_snapshot_error_for_caller(self):
        listener = _DocumentCloseListener(
            FakeDocument(fail=True),
            "file:///tmp/final.doc",
            lambda: None,
            (FakeUno().createUnoStruct("com.sun.star.beans.PropertyValue"),),
            Lock(),
            Event(),
        )
        listener.queryClosing(object(), False)
        self.assertTrue(listener.snapshot_ready.is_set())
        self.assertIsInstance(listener.snapshot_error, RuntimeError)

    def test_modify_listener_forwards_document_change(self):
        changes = []
        listener = _ModifyListener(lambda: changes.append("changed") or 1)
        listener.modified(object())
        listener.disposing(object())
        self.assertEqual(changes, ["changed"])


if __name__ == "__main__":
    unittest.main()
