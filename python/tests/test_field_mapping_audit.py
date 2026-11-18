import unittest

from emwat_linux.field_mapping_audit import audit_writer_property_alignment
from emwat_linux.word_fields import build_word_custom_property_field_maps
from emwat_linux.writer_inspector import WriterDocumentCatalog, WriterTextFieldInfo


class WriterPropertyAlignmentAuditTests(unittest.TestCase):
    def test_reports_exact_matches_without_claiming_order_equivalence(self):
        word = build_word_custom_property_field_maps(
            ["LetterSubject", "SignerPerson†SignerUnit", "WordOnly"]
        )
        writer = WriterDocumentCatalog(
            bookmarks=(), named_ranges=(), text_sections=(), text_tables=(),
            text_frames=(), graphic_objects=(), document_indexes=(),
            text_fields=(WriterTextFieldInfo(
                implementation_name="CustomField", property_names=("Name",),
                supported_services=("com.sun.star.text.TextField.DocInfo.Custom",),
                custom_property_name="LetterSubject",
            ),),
            custom_document_properties=("WriterOnly", "SignerPerson†SignerUnit", "LetterSubject"),
            custom_document_properties_in_info_order=("WriterOnly", "SignerPerson†SignerUnit", "LetterSubject"),
        )

        audit = audit_writer_property_alignment(word, writer)

        self.assertEqual(
            audit.exact_name_matches,
            ("LetterSubject", "SignerPerson†SignerUnit"),
        )
        self.assertEqual(audit.word_only_names, ("WordOnly",))
        self.assertEqual(audit.writer_only_names, ("WriterOnly", ""))
        self.assertEqual(audit.writer_docinfo_custom_field_names, ("LetterSubject",))
        self.assertEqual(audit.writer_property_names, (
            "WriterOnly", "SignerPerson†SignerUnit", "LetterSubject"
        ))

    def test_case_mismatch_is_not_silently_normalized(self):
        word = build_word_custom_property_field_maps(["LetterSubject"])
        writer = WriterDocumentCatalog(
            bookmarks=(), named_ranges=(), text_sections=(), text_tables=(),
            text_frames=(), graphic_objects=(), document_indexes=(), text_fields=(),
            custom_document_properties=("lettersubject",),
            custom_document_properties_in_info_order=("lettersubject",),
        )
        audit = audit_writer_property_alignment(word, writer)
        self.assertEqual(audit.exact_name_matches, ())
        self.assertEqual(audit.word_only_names, ("LetterSubject",))
        self.assertEqual(audit.writer_only_names, ("lettersubject",))


if __name__ == "__main__":
    unittest.main()
