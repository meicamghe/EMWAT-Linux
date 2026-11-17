"""Real Writer template-mapping integration test (dedicated UNO CI only)."""
import base64
import io
import os
import shutil
import unittest
import zipfile

from emwat_linux.editword_request import EditWordDocumentRequest
from emwat_linux.libreoffice_adapter import LibreOfficeAdapter
from emwat_linux.template_mapping import inspect_template_mapping
from emwat_linux.word_config import parse_word_config


@unittest.skipUnless(
    os.environ.get("EMWAT_RUN_LIBREOFFICE_INTEGRATION") == "1"
    and shutil.which("soffice"),
    "LibreOffice integration dependencies are not installed",
)
class LibreOfficeTemplateMappingTests(unittest.TestCase):
    def test_maps_config_property_to_real_writer_bookmark_and_docproperty_field(self):
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
                '<w:r><w:t>synthetic fixture</w:t></w:r><w:bookmarkEnd w:id="1"/></w:p>'
                '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
                '<w:r><w:instrText xml:space="preserve"> DOCPROPERTY  LetterSubject  \\* MERGEFORMAT </w:instrText></w:r>'
                '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
                '<w:r><w:t>fixture subject</w:t></w:r>'
                '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
                '<w:sectPr/></w:body></w:document>',
            )
            docx.writestr(
                "docProps/custom.xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
                'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
                '<property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2" name="LetterSubject">'
                '<vt:lpwstr>fixture subject</vt:lpwstr></property></Properties>',
            )

        config_xml = b'<word-document><fields><field id="subject-id"/></fields></word-document>'
        config = parse_word_config(base64.b64encode(config_xml).decode("ascii"))
        request = EditWordDocumentRequest(
            config=config,
            document_bytes=archive.getvalue(),
            sign_data_text="",
            extra_parameters={},
        )
        adapter = LibreOfficeAdapter(
            headless=True,
            connect_timeout_seconds=30,
            close_timeout_seconds=10,
        )
        handle = adapter.open_document(
            request,
            on_modified=lambda: 1,
            on_saved=lambda: None,
        )
        try:
            catalog = adapter.inspect_document(handle)
            report = inspect_template_mapping(config, catalog)
            self.assertTrue(report.index_alignment_valid)
            self.assertEqual(report.property_count, 1)
            self.assertEqual(report.config_field_count, 1)
            self.assertEqual(
                {
                    (candidate.config_index, candidate.xml_field_id, candidate.structure_kind, candidate.structure_name)
                    for candidate in report.candidates
                },
                {
                    (0, "subject-id", "bookmark", "LetterSubject"),
                    (0, "subject-id", "custom_property_text_field", "LetterSubject"),
                },
            )
        finally:
            try:
                handle.document.close(True)
                adapter.wait_for_close(handle)
            finally:
                if handle.process.poll() is None:
                    adapter._cleanup(handle)


if __name__ == "__main__":
    unittest.main()
