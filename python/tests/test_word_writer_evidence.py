import unittest

from emwat_linux.word_config import parse_word_config
from emwat_linux.word_writer_evidence import build_word_writer_evidence_report
from emwat_linux.writer_inspector import WriterDocumentCatalog, WriterTextFieldInfo


def empty_catalog(**overrides):
    values = dict(
        bookmarks=("LetterSubject",),
        named_ranges=("SignerBlock",),
        text_sections=("MainSection",),
        text_tables=("Recipients",),
        text_frames=("HeaderFrame",),
        graphic_objects=("SignatureImage",),
        document_indexes=(),
        text_fields=(
            WriterTextFieldInfo(
                implementation_name="DocInfoCustom",
                property_names=("Name",),
                supported_services=("com.sun.star.text.TextField.DocInfo.Custom",),
                custom_property_name="LetterSubject",
            ),
        ),
        custom_document_properties=("LetterSubject", "SignerPair"),
        custom_document_properties_in_info_order=("SignerPair", "LetterSubject"),
    )
    values.update(overrides)
    return WriterDocumentCatalog(**values)


class WordWriterEvidenceReportTests(unittest.TestCase):
    def test_reports_identifiers_and_metadata_without_field_values(self):
        config = parse_word_config(
            __import__("base64").b64encode(
                (
                    "<word-document><settings><setting name='readOnly'>false</setting></settings>"
                    "<fields>"
                    "<field id='subject' mimetype='text/plain' encryption='urlencoded'>SECRET-TEXT</field>"
                    "<field id='signature' mimetype='image/png' encryption='base64'>AQID</field>"
                    "<field id='signature' mimetype='image/png' paramId='signData'></field>"
                    "</fields>"
                    "<optional-attributes><attribute id='tokenizedReceivers' type='compInfo'>"
                    "<content>PRIVATE-VALUE</content></attribute></optional-attributes>"
                    "<requested-types><type name='document' mimetype='application/msword'/></requested-types>"
                    "</word-document>"
                ).encode()
            ).decode()
        )

        report = build_word_writer_evidence_report(config, empty_catalog())

        self.assertEqual([item.field_id for item in report.fields], ["subject", "signature", "signature"])
        self.assertEqual(report.duplicate_field_ids, ("signature",))
        self.assertEqual(report.fields[0].encoding, "urlencoded")
        self.assertTrue(report.fields[0].is_plain_text)
        self.assertTrue(report.fields[1].is_image)
        self.assertEqual(report.fields[2].external_parameter, "signData")
        self.assertEqual(report.settings_names, ("readOnly",))
        self.assertEqual(report.optional_attribute_ids, ("tokenizedReceivers",))
        self.assertEqual(
            report.requested_type_attributes,
            ((("mimetype", "application/msword"), ("name", "document")),),
        )
        self.assertEqual(report.writer_bookmark_names, ("LetterSubject",))
        self.assertEqual(report.writer_custom_property_names, ("SignerPair", "LetterSubject"))
        self.assertEqual(report.writer_docinfo_custom_field_names, ("LetterSubject",))
        self.assertNotIn("SECRET-TEXT", repr(report))
        self.assertNotIn("PRIVATE-VALUE", repr(report))

    def test_empty_config_and_writer_inventory_produce_empty_evidence(self):
        config = parse_word_config(
            __import__("base64").b64encode(b"<word-document/>").decode()
        )
        catalog = empty_catalog(
            bookmarks=(), named_ranges=(), text_sections=(), text_tables=(),
            text_frames=(), graphic_objects=(), text_fields=(),
            custom_document_properties=(), custom_document_properties_in_info_order=(),
        )
        report = build_word_writer_evidence_report(config, catalog)
        self.assertEqual(report.fields, ())
        self.assertEqual(report.duplicate_field_ids, ())
        self.assertEqual(report.writer_bookmark_names, ())
        self.assertEqual(report.writer_custom_property_names, ())


if __name__ == "__main__":
    unittest.main()
