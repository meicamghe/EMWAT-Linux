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
        adapter = LibreOfficeAdapter(headless=True, connect_timeout_seconds=30, close_timeout_seconds=10)
        handle = adapter.open_document(
            request,
            on_modified=lambda: 1,
            on_saved=lambda: None,
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
            catalog = adapter.inspect_document(handle)
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
            handle.document.close(True)
            close_event = adapter.wait_for_close(handle)
            self.assertEqual(close_event.disposition, CloseDisposition.CLOSED)
            output = adapter.export_final_document(handle)
            self.assertTrue(output.startswith(_CFB_SIGNATURE))

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
            finally:
                if roundtrip_handle.process.poll() is None:
                    adapter._cleanup(roundtrip_handle)
        finally:
            if handle.process.poll() is None:
                adapter._cleanup(handle)


if __name__ == "__main__":
    unittest.main()
