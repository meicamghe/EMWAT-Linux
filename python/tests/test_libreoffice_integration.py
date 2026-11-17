"""Optional real LibreOffice UNO integration test (enabled in dedicated CI)."""
import base64
import io
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from threading import Thread
from urllib.parse import unquote, urlparse
import zipfile
import xml.etree.ElementTree as ET

from emwat_linux.bridge import BridgeRequest, BridgeResponse
from emwat_linux.editword_handler import create_editword_handler
from emwat_linux.editword_service import EditWordDocumentService
from emwat_linux.protocol import WORD_RESPONSE_CONTENT_TYPE, parse_method_call

from emwat_linux.editword_request import EditWordDocumentRequest
from emwat_linux.libreoffice_adapter import LibreOfficeAdapter, _CFB_SIGNATURE, _OfficeHandle
from emwat_linux.recovery_store import RecoverySnapshotStore
from emwat_linux.office_adapter import CloseDisposition
from emwat_linux.word_config import WordDocumentConfig




class DocumentCloseListenerRetryTests(unittest.TestCase):
    def test_snapshot_failure_is_cleared_when_close_is_retried(self):
        from threading import Event, Lock
        from emwat_linux.libreoffice_adapter import _DocumentCloseListener

        class FlakyDocument:
            def __init__(self):
                self.attempts = 0

            def storeToURL(self, _url, _properties):
                self.attempts += 1
                if self.attempts == 1:
                    raise RuntimeError("simulated_close_attempt_cancelled")

        document = FlakyDocument()
        listener = _DocumentCloseListener(
            document,
            "file:///tmp/emwat-final.doc",
            lambda: None,
            (),
            Lock(),
            Event(),
        )

        listener.queryClosing(None, False)
        self.assertIsInstance(listener.snapshot_error, RuntimeError)
        self.assertTrue(listener.snapshot_ready.is_set())

        listener.queryClosing(None, False)
        self.assertIsNone(listener.snapshot_error)
        self.assertTrue(listener.snapshot_ready.is_set())
        self.assertEqual(document.attempts, 2)


class RecoveryWorkerTests(unittest.TestCase):
    def test_worker_retries_transient_error_and_persists_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "recovery"
            work_dir = Path(temporary) / "work"
            work_dir.mkdir()
            store = RecoverySnapshotStore(root)
            session_id = store.create_session()
            payload = _CFB_SIGNATURE + b"periodic-recovery-fixture"

            class FlakyDocument:
                def __init__(self):
                    self.attempts = 0

                def storeToURL(self, url, _properties):
                    self.attempts += 1
                    if self.attempts == 1:
                        raise RuntimeError("transient_uno_snapshot_failure")
                    destination = Path(unquote(urlparse(url).path))
                    destination.write_bytes(payload)

            document = FlakyDocument()
            handle = _OfficeHandle(
                process=None,
                document=document,
                close_listener=None,
                work_dir=work_dir,
                recovery_session_id=session_id,
            )
            adapter = LibreOfficeAdapter(
                recovery_store=store,
                recovery_interval_seconds=0.01,
            )
            worker = Thread(target=adapter._recovery_loop, args=(handle,), daemon=True)
            handle.recovery_thread = worker
            worker.start()
            try:
                deadline = time.monotonic() + 3
                snapshots = store.list_snapshots()
                while not snapshots and time.monotonic() < deadline:
                    time.sleep(0.01)
                    snapshots = store.list_snapshots()
                self.assertTrue(snapshots, "recovery_worker_did_not_persist_snapshot")
                self.assertGreaterEqual(document.attempts, 2)
                self.assertIsNone(handle.recovery_error)
                self.assertEqual(store.load_snapshot(session_id), payload)
            finally:
                handle.recovery_stop.set()
                worker.join(timeout=2)
            self.assertFalse(worker.is_alive())


@unittest.skipUnless(
    os.environ.get("EMWAT_RUN_LIBREOFFICE_INTEGRATION") == "1"
    and shutil.which("soffice"),
    "LibreOffice integration dependencies are not installed",
)
class LibreOfficeIntegrationTests(unittest.TestCase):
    def test_real_uno_document_flows_through_editword_response_handler(self):
        class AutoClosingAdapter(LibreOfficeAdapter):
            def wait_for_close(self, handle):
                handle.document.close(True)
                return super().wait_for_close(handle)

        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as docx:
            docx.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                '</Types>',
            )
            docx.writestr(
                "_rels/.rels",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                '</Relationships>',
            )
            docx.writestr(
                "word/document.xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body><w:p><w:r><w:t>EMWAT handler integration</w:t></w:r></w:p>'
                '<w:sectPr/></w:body></w:document>',
            )

        config = base64.b64encode(
            b'<word-document status="edit"><fields/></word-document>'
        ).decode("ascii")
        body = base64.b64encode(archive.getvalue()).decode("ascii")
        call_xml = (
            '<emwat version="1.0"><method class="EditWordDocument">'
            f'<param name="wordConfig">{config}</param>'
            f'<param name="wordBody">{body}</param>'
            '<param name="signData"></param>'
            '</method></emwat>'
        ).encode("utf-8")
        call = parse_method_call(call_xml)
        bridge_request = BridgeRequest(
            path="/",
            query="invoke=integration-nonce",
            content_type="text/xml",
            origin="https://almas.example.test",
            body=call_xml,
        )

        adapter = AutoClosingAdapter(
            headless=True,
            connect_timeout_seconds=30,
            close_timeout_seconds=10,
        )
        service = EditWordDocumentService(adapter)
        handler = create_editword_handler(
            service,
            cancel_response_factory=lambda _result, _request: BridgeResponse(
                b"cancelled", content_type="text/plain", status=409
            ),
        )
        response = handler(call, bridge_request)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, WORD_RESPONSE_CONTENT_TYPE)

        root = ET.fromstring(response.body)
        self.assertEqual(root.tag, "response-word")
        self.assertEqual(root.attrib.get("status"), "success")
        result_type = root.find("./return-types/type")
        self.assertIsNotNone(result_type)
        self.assertEqual(result_type.attrib.get("mimetype"), "application/msword")
        self.assertEqual(result_type.attrib.get("encryption"), "base64")
        returned_document = base64.b64decode(result_type.text or "", validate=True)
        self.assertTrue(returned_document.startswith(_CFB_SIGNATURE))

    def test_open_close_and_export_docx_as_legacy_word(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as docx:
            docx.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                '<Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/>'
                '</Types>',
            )
            docx.writestr(
                "_rels/.rels",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties" Target="docProps/custom.xml"/>'
                '</Relationships>',
            )
            docx.writestr(
                "word/document.xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body><w:p><w:bookmarkStart w:id="1" w:name="LetterSubject"/>'
                '<w:r><w:t>EMWAT integration fixture</w:t></w:r>'
                '<w:bookmarkEnd w:id="1"/></w:p>'
                '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
                '<w:r><w:instrText xml:space="preserve"> DOCPROPERTY  EMWATIntegrationMarker  \\* MERGEFORMAT </w:instrText></w:r>'
                '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
                '<w:r><w:t>initial-fixture-value</w:t></w:r>'
                '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
                '<w:sectPr/></w:body></w:document>',
            )
            docx.writestr(
                "docProps/custom.xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
                'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
                '<property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2" name="EMWATIntegrationMarker">'
                '<vt:lpwstr>initial-fixture-value</vt:lpwstr></property></Properties>',
            )

        request = EditWordDocumentRequest(
            config=WordDocumentConfig(
                root_attributes={},
                permissions={},
                settings=(),
                fields=(),
                optional_attributes=(),
                requested_types=(),
            ),
            document_bytes=archive.getvalue(),
            sign_data_text="",
            extra_parameters={},
        )
        recovery_temp = tempfile.TemporaryDirectory()
        self.addCleanup(recovery_temp.cleanup)
        recovery_store = RecoverySnapshotStore(Path(recovery_temp.name) / "recovery")
        adapter = LibreOfficeAdapter(
            headless=True,
            connect_timeout_seconds=30,
            close_timeout_seconds=10,
            recovery_store=recovery_store,
            recovery_interval_seconds=0.2,
        )
        saved_events = []
        handle = adapter.open_document(
            request,
            on_modified=lambda: 1,
            on_saved=lambda: saved_events.append("saved"),
        )
        try:
            user_properties = handle.document.getDocumentProperties().getUserDefinedProperties()
            self.assertEqual(
                user_properties.getPropertyValue("EMWATIntegrationMarker"),
                "initial-fixture-value",
            )
            adapter.apply_custom_property_updates(
                handle,
                {"EMWATIntegrationMarker": "updated-fixture-value"},
            )
            self.assertEqual(
                user_properties.getPropertyValue("EMWATIntegrationMarker"),
                "updated-fixture-value",
            )
            self.assertIn(
                "updated-fixture-value",
                handle.document.getText().getString(),
            )
            property_info_order = tuple(
                str(item.Name) for item in user_properties.getPropertySetInfo().getProperties()
            )
            catalog = adapter.inspect_document(handle)
            self.assertEqual(
                catalog.custom_document_properties_in_info_order,
                property_info_order,
            )
            self.assertIn("LetterSubject", catalog.bookmarks)
            self.assertIn("EMWATIntegrationMarker", catalog.custom_document_properties)
            self.assertIn(
                "EMWATIntegrationMarker",
                tuple(
                    field.custom_property_name
                    for field in catalog.text_fields
                    if field.custom_property_name is not None
                ),
            )
            with handle.snapshot_lock:
                text = handle.document.getText()
                text.insertString(text.getEnd(), " periodic recovery dirty-state marker", False)
                modified_before_recovery = handle.document.isModified()
            self.assertTrue(modified_before_recovery)
            deadline = time.monotonic() + 10
            snapshots = recovery_store.list_snapshots()
            while not snapshots and time.monotonic() < deadline:
                time.sleep(0.05)
                snapshots = recovery_store.list_snapshots()
            self.assertTrue(snapshots, "periodic_recovery_snapshot_not_created")
            self.assertEqual(snapshots[0].session_id, handle.recovery_session_id)
            self.assertTrue(
                recovery_store.load_snapshot(handle.recovery_session_id).startswith(_CFB_SIGNATURE)
            )
            self.assertEqual(saved_events, [])
            with handle.snapshot_lock:
                self.assertEqual(handle.document.isModified(), modified_before_recovery)
            handle.document.close(True)
            close_event = adapter.wait_for_close(handle)
            self.assertEqual(close_event.disposition, CloseDisposition.CLOSED)
            output = adapter.export_final_document(handle)
            self.assertTrue(output.startswith(_CFB_SIGNATURE))
            self.assertEqual(recovery_store.list_snapshots(), ())

            # The real EMWAT request carries a legacy OLE/CFB .doc, not DOCX.
            # Reopen the exported CFB payload to verify the actual input path.
            roundtrip_request = EditWordDocumentRequest(
                config=request.config,
                document_bytes=output,
                sign_data_text=request.sign_data_text,
                extra_parameters=request.extra_parameters,
            )
            roundtrip_handle = adapter.open_document(
                roundtrip_request,
                on_modified=lambda: 1,
                on_saved=lambda: None,
            )
            try:
                self.assertEqual(roundtrip_handle.source_path.suffix, ".doc")
                self.assertIn(
                    "EMWAT integration fixture",
                    roundtrip_handle.document.getText().getString(),
                )
                roundtrip_properties = (
                    roundtrip_handle.document.getDocumentProperties()
                    .getUserDefinedProperties()
                )
                self.assertEqual(
                    roundtrip_properties.getPropertyValue("EMWATIntegrationMarker"),
                    "updated-fixture-value",
                )
                roundtrip_catalog = adapter.inspect_document(roundtrip_handle)
                self.assertIn("LetterSubject", roundtrip_catalog.bookmarks)
                roundtrip_handle.document.close(True)
                roundtrip_close = adapter.wait_for_close(roundtrip_handle)
                self.assertEqual(roundtrip_close.disposition, CloseDisposition.CLOSED)
                final_roundtrip = adapter.export_final_document(roundtrip_handle)
                self.assertTrue(final_roundtrip.startswith(_CFB_SIGNATURE))
                self.assertEqual(recovery_store.list_snapshots(), ())
            finally:
                if roundtrip_handle.process.poll() is None:
                    adapter._cleanup(roundtrip_handle)
        finally:
            if handle.process.poll() is None:
                adapter._cleanup(handle)


if __name__ == "__main__":
    unittest.main()
