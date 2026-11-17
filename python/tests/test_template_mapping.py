import base64
import unittest

from emwat_linux.template_mapping import inspect_template_mapping
from emwat_linux.word_config import parse_word_config
from emwat_linux.writer_inspector import WriterDocumentCatalog, WriterTextFieldInfo


def config(*field_ids):
    fields = "".join(f'<field id="{field_id}"/>' for field_id in field_ids)
    xml = f"<word-document><fields>{fields}</fields></word-document>"
    return parse_word_config(base64.b64encode(xml.encode()).decode())


def catalog(properties, *, bookmarks=(), ranges=(), custom_fields=()):
    return WriterDocumentCatalog(
        bookmarks=tuple(bookmarks),
        named_ranges=tuple(ranges),
        text_sections=(),
        text_tables=(),
        text_frames=(),
        graphic_objects=(),
        document_indexes=(),
        text_fields=tuple(
            WriterTextFieldInfo(
                implementation_name="WriterCustomField",
                property_names=("Name",),
                supported_services=("com.sun.star.text.TextField.DocInfo.Custom",),
                custom_property_name=name,
            )
            for name in custom_fields
        ),
        custom_document_properties=tuple(sorted(properties)),
        custom_document_properties_in_info_order=tuple(properties),
    )


class TemplateMappingTests(unittest.TestCase):
    def test_reports_exact_single_and_twin_candidates(self):
        report = inspect_template_mapping(
            config("subject-id", "sign-id"),
            catalog(
                ("LetterSubject", "SignStart†SignEnd"),
                bookmarks=("lettersubject",),
                ranges=("SignStart", "SignEnd"),
            ),
        )
        self.assertTrue(report.index_alignment_valid)
        self.assertEqual(
            [
                (item.config_index, item.xml_field_id, item.config_member, item.structure_kind)
                for item in report.candidates
            ],
            [
                (0, "subject-id", "LetterSubject", "bookmark"),
                (1, "sign-id", "SignStart", "named_range"),
                (1, "sign-id", "SignEnd", "named_range"),
            ],
        )
        self.assertEqual(report.unmatched_config_fields, ())

    def test_reports_custom_property_text_field_as_separate_candidate(self):
        report = inspect_template_mapping(
            config("subject-id"),
            catalog(("LetterSubject",), custom_fields=("letterSUBJECT",)),
        )
        self.assertEqual(len(report.candidates), 1)
        self.assertEqual(report.candidates[0].structure_kind, "custom_property_text_field")

    def test_refuses_positional_mapping_when_counts_differ(self):
        report = inspect_template_mapping(
            config("subject-id", "number-id"),
            catalog(("LetterSubject",), bookmarks=("LetterSubject", "LetterNumber")),
        )
        self.assertFalse(report.index_alignment_valid)
        self.assertEqual(
            report.alignment_error,
            "custom_property_and_config_field_counts_differ",
        )
        self.assertEqual(report.candidates, ())
        self.assertEqual(report.unmatched_config_fields, ("subject-id", "number-id"))

    def test_does_not_invent_fuzzy_or_semantic_matches(self):
        report = inspect_template_mapping(
            config("subject-id"),
            catalog(("LetterSubject",), bookmarks=("Subject",)),
        )
        self.assertEqual(report.candidates, ())
        self.assertEqual(report.unmatched_config_fields, ("subject-id",))
        self.assertEqual(report.unmatched_template_structures, ("bookmark:Subject",))


if __name__ == "__main__":
    unittest.main()
