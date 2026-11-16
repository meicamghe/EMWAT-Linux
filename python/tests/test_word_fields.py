import base64
import unittest

from emwat_linux.word_config import parse_word_config
from emwat_linux.word_fields import (
    WordFieldDecodeError,
    decode_optional_attributes,
    decode_word_fields,
    extract_docproperty_identifier,
    external_parameter_bindings,
    is_native_business_signature_end,
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

    def test_matches_native_business_signature_end_pattern(self):
        for field_name in ("signsenderend", "signsenderend0", "signsenderend12", "signend29"):
            with self.subTest(field_name=field_name):
                self.assertTrue(is_native_business_signature_end(field_name))

        for field_name in ("SignSenderEnd", "xsignSenderEnd", "signSenderStart", "signSenderEnd123", ""):
            with self.subTest(field_name=field_name):
                self.assertFalse(is_native_business_signature_end(field_name))

    def test_extracts_docproperty_identifier_from_word_field_code(self):
        code = r"DOCPROPERTY  LetterSubject  \* MERGEFORMAT"
        self.assertEqual(extract_docproperty_identifier(code), "LetterSubject")
        triple_space = "DOCPROPERTY    LetterSubject  \\* MERGEFORMAT"
        self.assertEqual(extract_docproperty_identifier(triple_space), "")

    def test_preserves_non_docproperty_and_matches_native_unterminated_copy(self):
        code = r"MERGEFIELD  LetterSubject  \* MERGEFORMAT"
        self.assertEqual(extract_docproperty_identifier(code), code)

        # Native Copy(..., Pos("  ") + 2, 255) leaves the copied identifier
        # intact when there is no following single space.
        unterminated = "DOCPROPERTY  LetterSubject"
        self.assertEqual(extract_docproperty_identifier(unterminated), "LetterSubject")

        # Delphi Pos returns 0 when the double-space delimiter is absent;
        # the native Copy then starts at character 2.
        missing_double_space = "DOCPROPERTY LetterSubject"
        self.assertEqual(extract_docproperty_identifier(missing_double_space), "OCPROPERTY")

    def test_docproperty_keyword_match_is_case_sensitive(self):
        code = r"docproperty  LetterSubject  \* MERGEFORMAT"
        self.assertEqual(extract_docproperty_identifier(code), code)

    def test_decodes_urlencoded_text_and_preserves_plain_text(self):
        config = parse(
            '<word-document><fields>'
            '<field id="LetterSubject" encryption="urlencoded">سلام%20دنیا</field>'
            '<field id="LetterProducerName">Plain%20Text</field>'
            '<field id="PlusSpace" encryption="urlencoded">a+b</field>'
            '<field id="LiteralPlus" encryption="urlencoded">a%2Bb</field>'
            '</fields></word-document>'
        )
        fields = decode_word_fields(config)
        self.assertEqual(fields[0].value, "سلام دنیا")
        self.assertEqual(
            extract_docproperty_identifier("DOCPROPERTY  A  \\* MERGEFORMAT"),
            "A",
        )
        plus_config = parse(
            '<word-document><fields><field id="PlusEncoded" encryption="urlencoded">'
            'A+B%20C</field></fields></word-document>'
        )
        self.assertEqual(decode_word_fields(plus_config)[0].value, "A B C")
        self.assertEqual(fields[1].value, "Plain%20Text")
        self.assertEqual(fields[2].value, "a b")
        self.assertEqual(fields[3].value, "a+b")

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
        self.assertTrue(field.is_image)

        unpadded_quartet = parse(
            '<word-document><fields><field id="raw" encryption="base64">AQID</field>'
            '</fields></word-document>'
        )
        self.assertEqual(decode_word_fields(unpadded_quartet)[0].value, b"\x01\x02\x03")

        single_padding = parse(
            '<word-document><fields><field id="two" encryption="base64">AQI=</field>'
            '</fields></word-document>'
        )
        self.assertEqual(decode_word_fields(single_padding)[0].value, b"\x01\x02")

    def test_preserves_external_parameter_binding_without_guessing_concatenation(self):
        config = parse(
            '<word-document><fields>'
            '<field id="SignsStart†SignsEnd" paramId="signData" '
            'separator="&amp;" concater="&#92;n" concator="|" encryption="base64" '
            'mimetype="image/*"></field>'
            '</fields></word-document>'
        )
        fields = decode_word_fields(config)
        self.assertEqual(fields[0].value, b"")
        self.assertEqual(fields[0].external_parameter, "signData")
        self.assertTrue(fields[0].is_image)
        self.assertEqual(fields[0].attributes["concater"], r"\n")
        self.assertEqual(fields[0].attributes["concator"], "|")
        self.assertEqual(fields[0].identifier.first, "SignsStart")
        self.assertEqual(fields[0].identifier.second, "SignsEnd")
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
            '<word-document><fields><field id="x" encryption="base64">AQID BA==</field></fields></word-document>',
            '<word-document><fields><field id="x" encryption="base64">AQIDB</field></fields></word-document>',
            '<word-document><fields><field id="x" encryption="urlencoded">bad%ZZ</field></fields></word-document>',
        )
        for xml in cases:
            with self.subTest(xml=xml), self.assertRaises(WordFieldDecodeError):
                decode_word_fields(parse(xml))


if __name__ == "__main__":
    unittest.main()
