import tempfile
import unittest
from unittest.mock import patch
from threading import Event, Lock
from pathlib import Path

from emwat_linux.word_config import parse_word_config
from emwat_linux.writer_inspector import WriterDocumentCatalog

from emwat_linux.libreoffice_adapter import (
    LibreOfficeAdapter,
    _OfficeHandle,
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
    def test_adapter_exposes_read_only_word_writer_evidence_audit(self):
        handle = _OfficeHandle(
            process=FakeProcess(),
            document=object(),
            close_listener=None,
            work_dir=Path("."),
            recovery_session_id="audit-session",
        )
        config = parse_word_config(
            __import__("base64").b64encode(
                b'<word-document><fields><field id="subject" mimetype="text/plain">secret</field><field id="primary&#8224;secondary" mimetype="text/plain">opaque</field></fields><optional-attributes><attribute id="optional"><content/></attribute></optional-attributes></word-document>'
            ).decode()
        )
        catalog = WriterDocumentCatalog(
            bookmarks=("LetterSubject",), named_ranges=(), text_sections=(),
            text_tables=(), text_frames=(), graphic_objects=(), document_indexes=(),
            text_fields=(), custom_document_properties=("LetterSubject",),
            custom_document_properties_in_info_order=("LetterSubject",),
        )
        adapter = LibreOfficeAdapter()
        with patch(
            "emwat_linux.libreoffice_adapter.inspect_writer_document",
            return_value=catalog,
        ):
            report = adapter.audit_word_writer_evidence(handle, config)

        self.assertEqual(report.fields[0].field_id, "subject")
        self.assertEqual(report.fields[1].twin_first_member, "primary")
        self.assertEqual(report.fields[1].twin_second_member, "secondary")
        self.assertTrue(report.optional_attributes[0].has_content)
        self.assertEqual(report.writer_bookmark_names, ("LetterSubject",))
        self.assertNotIn("secret", repr(report))
        with self.assertRaisesRegex(TypeError, "invalid_word_document_config"):
            adapter.audit_word_writer_evidence(handle, object())

    def test_adapter_timeouts_must_be_finite_positive_numbers(self):
        invalid_values = (True, False, float("nan"), float("inf"), float("-inf"), 10 ** 1000, 0, -1, "1")
        for parameter in (
            "connect_timeout_seconds",
            "poll_interval_seconds",
            "recovery_interval_seconds",
            "close_timeout_seconds",
        ):
            for value in invalid_values:
                with self.subTest(parameter=parameter, value=value):
                    with self.assertRaises(ValueError):
                        LibreOfficeAdapter(**{parameter: value})

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

    def test_adapter_close_trace_records_callback_order_without_payload(self):
        from emwat_linux.libreoffice_adapter import _DocumentEventListener

        handle = _OfficeHandle(
            process=FakeProcess(),
            document=FakeDocument(),
            close_listener=None,
            work_dir=Path("."),
            recovery_session_id="trace-session",
        )
        closed = Event()
        listener = _DocumentCloseListener(
            handle.document,
            "file:///tmp/final.doc",
            closed.set,
            fake_snapshot_properties(),
            handle.snapshot_lock,
            handle.recovery_stop,
            handle.close_trace,
        )
        save_listener = _DocumentEventListener(lambda: None, handle.close_trace)

        listener.queryClosing(object(), False)
        listener.notifyClosing(object())
        save_listener.documentEventOccured(
            type("Event", (), {"EventName": "OnSaveDone"})()
        )
        listener.notifyClosed(object())

        events = LibreOfficeAdapter().inspect_close_lifecycle_trace(handle)
        self.assertEqual(
            [event.name for event in events],
            ["query_closing", "snapshot_succeeded", "notify_closing", "save_done", "notify_closed"],
        )
        self.assertTrue(all(event.attempt == 1 for event in events))
        self.assertTrue(closed.is_set())
        self.assertNotIn("final.doc", repr(events))
        self.assertNotIn("document", repr(events))

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

    def test_close_listener_retries_after_a_vetoed_or_cancelled_attempt(self):
        document = FakeDocument(fail=True)
        closed = Event()
        listener = _DocumentCloseListener(
            document,
            "file:///tmp/final.doc",
            closed.set,
            fake_snapshot_properties(),
            Lock(),
            Event(),
        )

        listener.queryClosing(object(), False)
        self.assertTrue(listener.snapshot_ready.is_set())
        self.assertIsInstance(listener.snapshot_error, RuntimeError)
        self.assertFalse(closed.is_set())

        # The office UI can keep the document open after this close attempt.
        # A later attempt must clear the prior error and produce a fresh snapshot.
        document.fail = False
        listener.queryClosing(object(), False)
        self.assertTrue(listener.snapshot_ready.is_set())
        self.assertIsNone(listener.snapshot_error)
        self.assertEqual(len(document.calls), 1)
        self.assertFalse(closed.is_set())

        listener.notifyClosed(object())
        self.assertTrue(closed.is_set())

    def test_successful_snapshot_from_cancelled_close_is_replaced_on_retry(self):
        document = FakeDocument()
        closed = Event()
        listener = _DocumentCloseListener(
            document,
            "file:///tmp/final.doc",
            closed.set,
            fake_snapshot_properties(),
            Lock(),
            Event(),
        )

        listener.queryClosing(object(), False)
        self.assertTrue(listener.snapshot_ready.is_set())
        self.assertFalse(closed.is_set())

        # Simulate a cancelled first close; a later close attempt must take a
        # new snapshot rather than reusing the earlier attempt's result.
        listener.queryClosing(object(), False)
        self.assertTrue(listener.snapshot_ready.is_set())
        self.assertIsNone(listener.snapshot_error)
        self.assertEqual(len(document.calls), 2)
        self.assertFalse(closed.is_set())

        listener.notifyClosed(object())
        self.assertTrue(closed.is_set())

    def test_close_returns_final_snapshot_without_an_explicit_save_event(self):
        from emwat_linux.libreoffice_adapter import _DocumentEventListener

        document = FakeDocument()
        saved = []
        closed = Event()
        save_listener = _DocumentEventListener(lambda: saved.append(True))
        close_listener = _DocumentCloseListener(
            document,
            "file:///tmp/final.doc",
            closed.set,
            fake_snapshot_properties(),
            Lock(),
            Event(),
        )

        # No OnSaveDone/OnSaveAsDone event is delivered before the user closes.
        close_listener.queryClosing(object(), False)
        close_listener.notifyClosed(object())

        self.assertEqual(saved, [])
        self.assertEqual(len(document.calls), 1)
        self.assertTrue(close_listener.snapshot_ready.is_set())
        self.assertIsNone(close_listener.snapshot_error)
        self.assertTrue(closed.is_set())

    def test_document_event_listener_only_reports_confirmed_save_events(self):
        from emwat_linux.libreoffice_adapter import _DocumentEventListener

        saved = []
        listener = _DocumentEventListener(lambda: saved.append("saved"))
        for event_name in ("OnSave", "OnSaveAs", "OnSaveDone", "OnSaveAsDone", ""):
            listener.documentEventOccured(type("Event", (), {"EventName": event_name})())
        listener.disposing(object())
        self.assertEqual(saved, ["saved", "saved"])


if __name__ == "__main__":
    unittest.main()
