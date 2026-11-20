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
        custom_document_properties_in_info_order=("SignerPair", "LetterSubject", "lettersubject"),
    )
    values.update(overrides)
    return WriterDocumentCatalog(**values)


class WordWriterEvidenceReportTests(unittest.TestCase):
    def test_reports_identifiers_and_metadata_without_field_values(self):
        config = parse_word_config(
            __import__("base64").b64encode(
                (
                    "<word-document status='edit'><permission role='editor'/>""<settings><setting name='readOnly'>false</setting><setting name='readOnly'>true</setting></settings>"
                    "<fields>"
                    "<field id='subject' mimetype='text/plain' encryption='urlencoded'>SECRET-TEXT</field>"
                    "<field id='signature' mimetype='image/png' encryption='base64'>AQID</field>"
                    "<field id='signature' mimetype='image/png' paramId='signData'></field>""<field id='Subject' mimetype='TEXT/PLAIN'>OTHER-SECRET</field>"
                    "</fields>"
                    "<optional-attributes><attribute id='tokenizedReceivers' type='compInfo'>"
                    "<content encryption='urlencoded'>PRIVATE-VALUE</content></attribute>""<attribute id='tokenizedReceivers' type='compInfo'/></optional-attributes>"
                    "<requested-types><type name='document' mimetype='application/msword'/></requested-types>"
                    "</word-document>"
                ).encode()
            ).decode()
        )

        report = build_word_writer_evidence_report(config, empty_catalog())

        self.assertEqual([item.field_id for item in report.fields], ["subject", "signature", "signature", "Subject"])
        self.assertEqual(report.duplicate_field_ids, ("signature",))
        self.assertEqual(report.casefold_field_id_collisions, (("subject", "Subject"),))
        self.assertEqual(report.fields[3].index, 3)
        self.assertTrue(report.fields[3].is_plain_text)
        self.assertEqual(report.root_attribute_names, ("status",))
        self.assertEqual(report.permission_attribute_names, ("role",))
        self.assertEqual(report.duplicate_setting_names, ("readOnly",))
        self.assertEqual(report.duplicate_optional_attribute_ids, ("tokenizedReceivers",))
        self.assertEqual(report.optional_attributes[0].content_encoding, "urlencoded")
        self.assertTrue(report.optional_attributes[0].has_content)
        self.assertFalse(report.optional_attributes[1].has_content)
        self.assertEqual(report.writer_custom_property_casefold_collisions, (("LetterSubject", "lettersubject"),))
        self.assertEqual(report.fields[0].encoding, "urlencoded")
        self.assertTrue(report.fields[0].is_plain_text)
        self.assertTrue(report.fields[1].is_image)
        self.assertEqual(report.fields[2].external_parameter, "signData")
        self.assertEqual(report.settings_names, ("readOnly", "readOnly"))
        self.assertEqual(tuple(item.attribute_id for item in report.optional_attributes), ("tokenizedReceivers", "tokenizedReceivers"))
        self.assertEqual(
            report.requested_type_attributes,
            ((("mimetype", "application/msword"), ("name", "document")),),
        )
        self.assertEqual(report.writer_bookmark_names, ("LetterSubject",))
        self.assertEqual(report.writer_custom_property_names, ("SignerPair", "LetterSubject", "lettersubject"))
        self.assertEqual(report.writer_docinfo_custom_field_names, ("LetterSubject",))
        self.assertNotIn("SECRET-TEXT", repr(report))
        self.assertNotIn("PRIVATE-VALUE", repr(report))
        self.assertNotIn("OTHER-SECRET", repr(report))
        self.assertNotIn("editor", repr(report))
        self.assertNotIn("edit", repr(report))

    def test_reports_declared_twin_identifier_members_without_writer_pairing(self):
        xml = (
            b"<word-document><fields>"
            b"<field id='PrimaryName&#8224;SecondaryName' mimetype='text/plain'>opaque</field>"
            b"</fields></word-document>"
        )
        config = parse_word_config(__import__("base64").b64encode(xml).decode())
        report = build_word_writer_evidence_report(config, empty_catalog())
        field = report.fields[0]
        self.assertEqual(field.field_id, "PrimaryName†SecondaryName")
        self.assertEqual(field.twin_first_member, "PrimaryName")
        self.assertEqual(field.twin_second_member, "SecondaryName")
        self.assertNotIn("opaque", repr(report))

    def test_missing_optional_attribute_ids_are_not_reported_as_duplicates(self):
        xml = (
            b"<word-document><optional-attributes>"
            b"<attribute type='first'/><attribute type='second'/>"
            b"</optional-attributes></word-document>"
        )
        config = parse_word_config(__import__("base64").b64encode(xml).decode())
        report = build_word_writer_evidence_report(config, empty_catalog())
        self.assertEqual(report.duplicate_optional_attribute_ids, ())
        self.assertEqual(
            tuple(item.attribute_id for item in report.optional_attributes),
            ("", ""),
        )

    def test_rejects_invalid_input_types(self):
        config = parse_word_config(
            __import__("base64").b64encode(b"<word-document/>").decode()
        )
        catalog = empty_catalog()
        with self.assertRaisesRegex(TypeError, "invalid_word_document_config"):
            build_word_writer_evidence_report(object(), catalog)
        with self.assertRaisesRegex(TypeError, "invalid_writer_document_catalog"):
            build_word_writer_evidence_report(config, object())

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
