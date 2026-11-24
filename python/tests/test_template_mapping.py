import base64
import unittest

from emwat_linux.template_mapping import inspect_template_mapping
from emwat_linux.word_config import parse_word_config
from emwat_linux.writer_inspector import WriterDocumentCatalog, WriterTextFieldInfo


def config(*field_ids):
    fields = "".join(f'<field id="{field_id}"/>' for field_id in field_ids)
    xml = f"<word-document><fields>{fields}</fields></word-document>"
    return parse_word_config(base64.b64encode(xml.encode()).decode())


def catalog(properties, *, bookmarks=(), ranges=(), custom_fields=(), warnings=()):
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
        inspection_warnings=tuple(warnings),
    )


class TemplateMappingTests(unittest.TestCase):
    def test_reports_exact_single_and_twin_property_candidates_without_config_pairing(self):
        report = inspect_template_mapping(
            config("xml-subject-id", "xml-sign-id"),
            catalog(
                ("LetterSubject", "SignStart†SignEnd"),
                bookmarks=("lettersubject",),
                ranges=("SignStart", "SignEnd"),
            ),
        )
        self.assertTrue(report.property_config_counts_match)
        self.assertFalse(report.property_order_equivalence_verified)
        self.assertEqual(
            [(item.property_index, item.property_member, item.structure_kind)
             for item in report.candidates],
            [(0, "LetterSubject", "bookmark"),
             (1, "SignStart", "named_range"),
             (1, "SignEnd", "named_range")],
        )
        self.assertEqual(
            report.unassociated_config_field_ids, ("xml-subject-id", "xml-sign-id")
        )

    def test_reports_docinfo_custom_field_as_separate_candidate(self):
        report = inspect_template_mapping(
            config("xml-subject-id"),
            catalog(("LetterSubject",), custom_fields=("letterSUBJECT",)),
        )
        self.assertEqual(len(report.candidates), 1)
        self.assertEqual(report.candidates[0].structure_kind, "custom_property_text_field")

    def test_count_mismatch_does_not_create_xml_field_associations(self):
        report = inspect_template_mapping(
            config("xml-subject-id", "xml-number-id"),
            catalog(("LetterSubject",), bookmarks=("LetterSubject", "LetterNumber")),
        )
        self.assertFalse(report.property_config_counts_match)
        self.assertEqual(len(report.candidates), 1)
        self.assertEqual(
            report.unassociated_config_field_ids,
            ("xml-subject-id", "xml-number-id"),
        )

    def test_does_not_invent_fuzzy_or_semantic_matches(self):
        report = inspect_template_mapping(
            config("xml-subject-id"),
            catalog(("LetterSubject",), bookmarks=("Subject",)),
        )
        self.assertEqual(report.candidates, ())
        self.assertEqual(report.unmatched_custom_properties, ("LetterSubject",))
        self.assertEqual(report.unmatched_writer_structures, ("bookmark:Subject",))


    def test_maps_config_ids_directly_to_writer_structures_without_property_order(self):
        report = inspect_template_mapping(
            config("LetterSubject", "SignStart†SignEnd", "NoTarget"),
            catalog(
                (),
                bookmarks=("LetterSubject",),
                ranges=("SignStart", "SignEnd"),
            ),
        )
        self.assertEqual(
            [(item.field_index, item.field_member, item.structure_kind, item.match_kind)
             for item in report.config_field_candidates],
            [
                (0, "LetterSubject", "bookmark", "exact"),
                (1, "SignStart", "named_range", "exact"),
                (1, "SignEnd", "named_range", "exact"),
            ],
        )
        self.assertEqual(report.unmatched_config_field_indices, (2,))
        self.assertEqual(report.partial_config_field_indices, ())
        self.assertEqual(report.ambiguous_config_field_indices, ())
        self.assertFalse(report.property_order_equivalence_verified)

    def test_reports_partial_twin_and_ambiguous_direct_field_candidates(self):
        report = inspect_template_mapping(
            config("Start†Missing", "signature"),
            catalog((), ranges=("Start",), bookmarks=("Signature", "SIGNATURE")),
        )
        self.assertEqual(report.partial_config_field_indices, (0,))
        self.assertEqual(report.ambiguous_config_field_indices, (1,))
        self.assertEqual(
            [(item.field_index, item.field_member) for item in report.config_field_candidates],
            [(0, "Start")],
        )

    def test_prevents_two_config_fields_claiming_one_writer_structure(self):
        report = inspect_template_mapping(
            config("Signature", "signature"),
            catalog((), bookmarks=("Signature",)),
        )
        self.assertEqual(report.config_field_candidates, ())
        self.assertEqual(report.ambiguous_config_field_indices, (0, 1))

    def test_surfaces_duplicate_property_names_and_partial_inventory_warnings(self):
        report = inspect_template_mapping(
            config("xml-a", "xml-b"),
            catalog(
                ("LetterSubject", "lettersubject"),
                bookmarks=("LetterSubject",),
                warnings=("getTextFrames_unavailable",),
            ),
        )
        self.assertEqual(report.duplicate_property_names, ("lettersubject",))
        self.assertEqual(report.inspection_warnings, ("getTextFrames_unavailable",))


if __name__ == "__main__":
    unittest.main()
