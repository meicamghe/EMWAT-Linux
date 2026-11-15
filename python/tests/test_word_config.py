import base64
import unittest

from emwat_linux.word_config import WordConfigError, parse_word_config


def encoded(xml: str) -> str:
    return base64.b64encode(xml.encode("utf-8")).decode("ascii")


class WordConfigTests(unittest.TestCase):
    def test_parses_captured_configuration_layers_without_decoding_field_values(self):
        xml = (
            '<word-document status="edit">'
            '<permission allowCopy="true" allowPrint="false" allowSave="true"/>'
            '<settings><setting name="gam-print-dialog">false</setting></settings>'
            '<fields>'
            '<field id="LetterSubject" encryption="urlencoded">A%20B</field>'
            '<field id="SignOfSignerStart0†SignOfSignerEnd0" '
            'encryption="base64" mimetype="image/*">AQID</field>'
            '</fields>'
            '<optional-attributes><attribute id="tokenizedReceivers" type="compInfo">'
            '<content encryption="urlencoded">receiver%3D1</content>'
            '</attribute></optional-attributes>'
            '<requested-types><type mimetype="application/msword"/></requested-types>'
            '</word-document>'
        )
        config = parse_word_config(encoded(xml))
        self.assertEqual(config.root_attributes["status"], "edit")
        self.assertEqual(config.permissions["allowPrint"], "false")
        self.assertEqual(config.settings[0].name, "gam-print-dialog")
        self.assertEqual(config.settings[0].value, "false")
        self.assertEqual(config.fields[0].field_id, "LetterSubject")
        self.assertEqual(config.fields[0].text, "A%20B")
        self.assertEqual(config.fields[1].text, "AQID")
        self.assertEqual(config.fields[1].attributes["mimetype"], "image/*")
        self.assertEqual(config.optional_attributes[0].attributes["type"], "compInfo")
        self.assertEqual(config.optional_attributes[0].content, "receiver%3D1")
        self.assertEqual(config.requested_types[0]["mimetype"], "application/msword")

    def test_accepts_xml_whitespace_in_base64(self):
        value = encoded('<word-document status="edit"/>')
        spaced = value[:8] + "\n  " + value[8:]
        self.assertEqual(parse_word_config(spaced).root_attributes["status"], "edit")

    def test_preserves_duplicate_field_ids_and_order(self):
        xml = (
            '<word-document><fields>'
            '<field id="x">first</field><field id="x">second</field>'
            '</fields></word-document>'
        )
        config = parse_word_config(encoded(xml))
        self.assertEqual([item.text for item in config.fields], ["first", "second"])

    def test_rejects_invalid_base64_and_non_utf8(self):
        for value in ("not-base64!", "%%%"):
            with self.subTest(value=value), self.assertRaises(WordConfigError):
                parse_word_config(value)
        bad_utf8 = base64.b64encode(b"\xff").decode("ascii")
        with self.assertRaises(WordConfigError):
            parse_word_config(bad_utf8)

    def test_rejects_dtd_entities_and_wrong_root(self):
        cases = (
            '<!DOCTYPE word-document [<!ENTITY x "bad">]><word-document/>',
            '<other/>',
        )
        for xml in cases:
            with self.subTest(xml=xml), self.assertRaises(WordConfigError):
                parse_word_config(encoded(xml))

    def test_rejects_missing_field_id_and_invalid_nested_content(self):
        cases = (
            '<word-document><fields><field>value</field></fields></word-document>',
            '<word-document><fields><field id="x"><nested/></field></fields></word-document>',
            '<word-document><settings><setting>value</setting></settings></word-document>',
        )
        for xml in cases:
            with self.subTest(xml=xml), self.assertRaises(WordConfigError):
                parse_word_config(encoded(xml))

    def test_enforces_encoded_and_decoded_size_limits(self):
        value = encoded('<word-document/>')
        with self.assertRaises(WordConfigError):
            parse_word_config(value, max_encoded_chars=4)
        with self.assertRaises(WordConfigError):
            parse_word_config(value, max_decoded_bytes=4)

    def test_rejects_non_text_input(self):
        with self.assertRaises(TypeError):
            parse_word_config(b"<word-document/>")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
