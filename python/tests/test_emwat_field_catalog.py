import unittest

from emwat_linux.emwat_field_catalog import (
    build_indexed_signer_slots,
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

    def test_builds_indexed_slots_and_reports_missing_families(self):
        fields = (
            "LetterSignerPer3",
            "LetterSignerDep1",
            "SignNumberOfSigner3",
            "LetterSignerUnit1",
            "LetterSignerDep3",
        )
        slots = build_indexed_signer_slots(fields)
        self.assertEqual([slot.index for slot in slots], [1, 3])
        self.assertFalse(slots[0].complete)
        self.assertEqual(
            [field.field_id for field in slots[0].fields],
            ["LetterSignerDep1", "LetterSignerUnit1"],
        )
        self.assertEqual(
            slots[1].missing_families,
            ("unit", "index_unit", "behalf_name", "signature_image"),
        )
        self.assertEqual(
            [field.field_id for field in slots[1].fields],
            ["LetterSignerPer3", "SignNumberOfSigner3", "LetterSignerDep3"],
        )

    def test_builds_duplicate_field_occurrences_in_original_order(self):
        fields = (
            "LetterSignerPer2",
            "LetterSignerDep2",
            "LetterSignerPer2",
            "SignNumberOfSigner2",
        )
        slots = build_indexed_signer_slots(fields)
        self.assertEqual(len(slots), 1)
        self.assertEqual(
            [field.field_id for field in slots[0].fields],
            [
                "LetterSignerPer2",
                "LetterSignerDep2",
                "LetterSignerPer2",
                "SignNumberOfSigner2",
            ],
        )
        self.assertEqual(
            [field.family for field in slots[0].fields],
            ["person", "department", "person", "signature_number"],
        )


    def test_catalogs_all_forty_base_fields_and_indexed_signer_families(self):
        from emwat_linux.emwat_field_catalog import build_word_config_field_catalog

        base_ids = ["RelatedLetters","LetterDescription","LetterSubject","Appendix","HasAppendix","Version","letterId","LetterProducerName","LetterProducerDep","LetterProducerDepPhoneNumber","LetterProducerPhoneNumber","LetterProducerUnit","LetterProducerUnitCode","LetterSenderName","LetterSenderDep","LetterSenderAddress","LetterSenderUnit","LetterSenderUnitCode","LetterSenderIndexUnit","ProduceDate","LetterRegistrationNo","LetterRegistrationDate","LetterRegistrationTime","Classification","TransferType","DocType","Priority","Receivers","ReceiverDeps","ReceiverCeremonialUnits","ccReceivers","ccReceiverDeps","ccReceiverCeremonialUnits","SenderSignerBehalfName","SignNumberOfSender","SignOfSenderStart†SignOfSenderEnd","ShamsQRcodeStart†ShamsQRcodeEnd","shamsBarcode","Slogan","SignsStart†SignsEnd"]
        fields = tuple(base_ids) + (
            "LetterSignerPer0",
            "SignOfSignerStart19†SignOfSignerEnd19",
            "UnknownFutureField",
        )
        catalog = build_word_config_field_catalog(fields)
        self.assertEqual(len(catalog.base_fields), 40)
        self.assertEqual(len(catalog.indexed_signer_fields), 2)
        self.assertEqual(catalog.unknown_fields, ((42, "UnknownFutureField"),))
        self.assertEqual(
            catalog.base_fields[-5].category, "sender_signature_metadata"
        )
        self.assertEqual(
            catalog.base_fields[-4].category, "sender_signature_image"
        )
        self.assertEqual(
            catalog.base_fields[-1].category, "external_signature_parameter"
        )

    def test_rejects_non_text_field_ids(self):
        with self.assertRaisesRegex(TypeError, "field_id_must_be_text"):
            parse_indexed_signer_field(None)


if __name__ == "__main__":
    unittest.main()
