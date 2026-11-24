import base64
import unittest

from emwat_linux.image_mapping import inspect_word_image_mapping
from emwat_linux.word_config import parse_word_config
from emwat_linux.writer_inspector import WriterDocumentCatalog


def config(*fields):
    body = "".join(fields)
    xml = f"<word-document><fields>{body}</fields></word-document>"
    return parse_word_config(base64.b64encode(xml.encode()).decode())


def catalog(*names):
    return WriterDocumentCatalog(
        bookmarks=(), named_ranges=(), text_sections=(), text_tables=(),
        text_frames=(), graphic_objects=tuple(names), document_indexes=(),
        text_fields=(), custom_document_properties=(),
        custom_document_properties_in_info_order=(),
    )


class WordImageMappingTests(unittest.TestCase):
    def test_exact_and_twin_member_candidates_are_read_only(self):
        report = inspect_word_image_mapping(
            config(
                "<field id='Logo' mimetype='image/png'/>",
                "<field id='SignatureStart†SignatureEnd' mimetype='image/png'/>",
            ),
            catalog("Logo", "SignatureEnd"),
        )
        self.assertEqual(report.image_field_count, 2)
        self.assertEqual(
            [(item.field_index, item.matched_member, item.match_kind)
             for item in report.candidates],
            [(0, "Logo", "exact"), (1, "SignatureEnd", "exact")],
        )
        self.assertEqual(report.unmatched_image_field_indices, ())
        self.assertEqual(report.ambiguous_image_field_indices, ())

    def test_unique_casefold_candidate_is_only_a_review_hint(self):
        report = inspect_word_image_mapping(
            config("<field id='signature' mimetype='image/png'/>"),
            catalog("Signature"),
        )
        self.assertEqual(report.candidates[0].match_kind, "casefold")

    def test_casefold_collision_is_ambiguous(self):
        report = inspect_word_image_mapping(
            config("<field id='signature' mimetype='image/png'/>"),
            catalog("Signature", "SIGNATURE"),
        )
        self.assertEqual(report.candidates, ())
        self.assertEqual(report.ambiguous_image_field_indices, (0,))

    def test_one_graphic_cannot_be_assigned_to_duplicate_image_fields(self):
        report = inspect_word_image_mapping(
            config(
                "<field id='Signature' mimetype='image/png'/>",
                "<field id='Signature' mimetype='image/png'/>",
            ),
            catalog("Signature"),
        )
        self.assertEqual(report.candidates, ())
        self.assertEqual(report.ambiguous_image_field_indices, (0, 1))

    def test_non_image_fields_are_ignored_and_unmatched_images_reported(self):
        report = inspect_word_image_mapping(
            config(
                "<field id='LetterSubject' mimetype='text/plain'>x</field>",
                "<field id='QR' mimetype='image/png'/>",
            ),
            catalog("OtherGraphic"),
        )
        self.assertEqual(report.image_field_count, 1)
        self.assertEqual(report.unmatched_image_field_indices, (1,))


if __name__ == "__main__":
    unittest.main()
