import base64
import unittest

from emwat_linux.word_config import parse_word_config
from emwat_linux.word_fields import (
    WordFieldDecodeError,
    decode_optional_attributes,
    decode_word_fields,
    external_parameter_bindings,
    parse_word_field_identifier,
)


def parse(xml: str):
    encoded = base64.b64encode(xml.encode("utf-8")).decode("ascii")
    return parse_word_config(encoded)


class WordFieldDecodingTests(unittest.TestCase):
    def test_parses_single_and_twin_field_identifiers_using_dagger(self):
        single = parse_word_field_identifier("LetterSubject")
        self.assertEqual(single.first, "LetterSubject")
        self.assertIsNone(single.second)
        self.assertFalse(single.is_twin)

        twin = parse_word_field_identifier("SignsStart†SignsEnd")
        self.assertEqual(twin.first, "SignsStart")
        self.assertEqual(twin.second, "SignsEnd")
        self.assertTrue(twin.is_twin)

        multiple = parse_word_field_identifier("A†B†C")
        self.assertEqual(multiple.first, "A")
        self.assertEqual(multiple.second, "B†C")
        self.assertTrue(multiple.is_twin)

        for malformed in ("†Tail", "Head†"):
            parsed = parse_word_field_identifier(malformed)
            self.assertEqual(parsed.first, malformed)
            self.assertIsNone(parsed.second)

    def test_decodes_urlencoded_text_and_preserves_plain_text(self):
        config = parse(
            '<word-document><fields>'
            '<field id="LetterSubject" encryption="urlencoded">سلام%20دنیا</field>'
            '<field id="LetterProducerName">Plain%20Text</field>'
            '</fields></word-document>'
        )
        fields = decode_word_fields(config)
        self.assertEqual(fields[0].value, "سلام دنیا")
        self.assertEqual(fields[1].value, "Plain%20Text")

    def test_decodes_base64_image_bytes(self):
        config = parse(
            '<word-document><fields>'
            '<field id="SignOfSenderStart†SignOfSenderEnd" '
            'encryption="base64" mimetype="image/png">AQIDBA==</field>'
            '</fields></word-document>'
        )
        field = decode_word_fields(config)[0]
        self.assertEqual(field.value, bytes.fromhex("01020304"))
        self.assertEqual(field.mimetype, "image/png")

    def test_preserves_external_parameter_binding_without_guessing_concatenation(self):
        config = parse(
            '<word-document><fields>'
            '<field id="SignsStart†SignsEnd" paramId="signData" '
            'separator="&amp;" concater="&#10;" encryption="base64" '
            'mimetype="image/*"></field>'
            '</fields></word-document>'
        )
        fields = decode_word_fields(config)
        self.assertEqual(fields[0].value, b"")
        self.assertEqual(fields[0].external_parameter, "signData")
        self.assertEqual(external_parameter_bindings(fields), fields)

    def test_decodes_optional_attribute_using_nested_encoding(self):
        config = parse(
            '<word-document><optional-attributes>'
            '<attribute id="tokenizedReceivers" type="compInfo">'
            '<content encryption="urlencoded">receiver%3D1</content>'
            '</attribute></optional-attributes></word-document>'
        )
        attributes = decode_optional_attributes(config)
        self.assertEqual(attributes[0].attribute_id, "tokenizedReceivers")
        self.assertEqual(attributes[0].value_type, "compInfo")
        self.assertEqual(attributes[0].value, "receiver=1")

    def test_rejects_unknown_or_malformed_encodings(self):
        cases = (
            '<word-document><fields><field id="x" encryption="rot13">abc</field></fields></word-document>',
            '<word-document><fields><field id="x" encryption="base64">not-base64!</field></fields></word-document>',
            '<word-document><fields><field id="x" encryption="urlencoded">bad%ZZ</field></fields></word-document>',
        )
        for xml in cases:
            with self.subTest(xml=xml), self.assertRaises(WordFieldDecodeError):
                decode_word_fields(parse(xml))


if __name__ == "__main__":
    unittest.main()
