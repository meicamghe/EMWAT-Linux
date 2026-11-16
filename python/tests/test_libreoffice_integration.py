"""Optional real LibreOffice UNO integration test (enabled in dedicated CI)."""
import io
import os
import shutil
import unittest
import zipfile

from emwat_linux.editword_request import EditWordDocumentRequest
from emwat_linux.libreoffice_adapter import LibreOfficeAdapter, _CFB_SIGNATURE
from emwat_linux.office_adapter import CloseDisposition
from emwat_linux.word_config import WordDocumentConfig


@unittest.skipUnless(
    os.environ.get("EMWAT_RUN_LIBREOFFICE_INTEGRATION") == "1"
    and shutil.which("soffice"),
    "LibreOffice integration dependencies are not installed",
)
class LibreOfficeIntegrationTests(unittest.TestCase):
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
                '<w:body><w:p><w:bookmarkStart w:id="1" w:name="LetterSubject"/>'
                '<w:r><w:t>EMWAT integration fixture</w:t></w:r>'
                '<w:bookmarkEnd w:id="1"/></w:p><w:sectPr/></w:body></w:document>',
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
        adapter = LibreOfficeAdapter(headless=True, connect_timeout_seconds=30, close_timeout_seconds=10)
        handle = adapter.open_document(
            request,
            on_modified=lambda: 1,
            on_saved=lambda: None,
        )
        try:
            user_properties = handle.document.getDocumentProperties().getUserDefinedProperties()
            user_properties.addProperty("EMWATIntegrationMarker", 0, "do-not-read-this-value")
            catalog = adapter.inspect_document(handle)
            self.assertIn("LetterSubject", catalog.bookmarks)
            self.assertIn("EMWATIntegrationMarker", catalog.custom_document_properties)
            handle.document.close(True)
            close_event = adapter.wait_for_close(handle)
            self.assertEqual(close_event.disposition, CloseDisposition.CLOSED)
            output = adapter.export_final_document(handle)
            self.assertTrue(output.startswith(_CFB_SIGNATURE))
        finally:
            if handle.process.poll() is None:
                adapter._cleanup(handle)


if __name__ == "__main__":
    unittest.main()
