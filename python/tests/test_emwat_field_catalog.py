import unittest

from emwat_linux.emwat_field_catalog import (
    group_indexed_signer_fields,
    parse_indexed_signer_field,
)


class EmwatFieldCatalogTests(unittest.TestCase):
    def test_recognizes_all_seven_indexed_signer_families(self):
        cases = (
            ("LetterSignerDep0", "department", 0),
            ("LetterSignerPer19", "person", 19),
            ("LetterSignerUnit3", "unit", 3),
            ("LetterSignerIndexUnit4", "index_unit", 4),
            ("SignNumberOfSigner5", "signature_number", 5),
            ("BehalfNameOfSigner6", "behalf_name", 6),
            ("SignOfSignerStart7†SignOfSignerEnd7", "signature_image", 7),
        )
        for field_id, family, index in cases:
            with self.subTest(field_id=field_id):
                parsed = parse_indexed_signer_field(field_id)
                self.assertIsNotNone(parsed)
                self.assertEqual((parsed.family, parsed.index, parsed.field_id),
                                 (family, index, field_id))

    def test_rejects_malformed_or_non_signer_ids_without_guessing(self):
        for field_id in (
            "LetterSubject",
            "SignOfSignerStart7†SignOfSignerEnd8",
            "LetterSignerDep",
            "LetterSignerPer-1",
            "signNumberOfSigner2",
        ):
            with self.subTest(field_id=field_id):
                self.assertIsNone(parse_indexed_signer_field(field_id))

    def test_groups_fields_and_preserves_capture_order(self):
        fields = (
            "LetterSignerPer2",
            "LetterSubject",
            "LetterSignerPer0",
            "SignNumberOfSigner2",
        )
        grouped = group_indexed_signer_fields(fields)
        self.assertEqual(
            [item.field_id for item in grouped["person"]],
            ["LetterSignerPer2", "LetterSignerPer0"],
        )
        self.assertEqual(
            [item.index for item in grouped["signature_number"]],
            [2],
        )
        self.assertEqual(grouped["department"], ())

    def test_rejects_non_text_field_ids(self):
        with self.assertRaisesRegex(TypeError, "field_id_must_be_text"):
            parse_indexed_signer_field(None)


if __name__ == "__main__":
    unittest.main()
