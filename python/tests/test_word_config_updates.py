import base64
import unittest

from emwat_linux.word_config import parse_word_config
from emwat_linux.word_config_updates import (
    WordConfigTextUpdateError,
    as_custom_property_update_mapping,
    build_word_config_text_updates,
)


def config(xml):
    return parse_word_config(base64.b64encode(xml.encode()).decode())


class WordConfigTextUpdateTests(unittest.TestCase):
    def test_decodes_explicit_urlencoded_text_and_preserves_empty_values(self):
        parsed = config(
            "<word-document><fields>"
            "<field id='Subject' mimetype='text/plain' encryption='urlencoded'>"
            "%D9%85%D9%88%D8%B6%D9%88%D8%B9"
            "</field>"
            "<field id='Empty' mimetype='text/plain'/>"
            "</fields></word-document>"
        )
        updates = build_word_config_text_updates(parsed, {0: "EMWATSubject", 1: "EMWATEmpty"})
        self.assertEqual(
            [(item.field_index, item.field_id, item.target_property_name)
             for item in updates],
            [(0, "Subject", "EMWATSubject"), (1, "Empty", "EMWATEmpty")],
        )
        self.assertEqual(
            dict(as_custom_property_update_mapping(updates)),
            {"EMWATSubject": "موضوع", "EMWATEmpty": ""},
        )
        self.assertNotIn("موضوع", repr(updates))

    def test_rejects_image_and_external_parameter_fields(self):
        parsed = config(
            "<word-document><fields>"
            "<field id='Logo' mimetype='image/png' encryption='base64'>AQID</field>"
            "<field id='SignsStart†SignsEnd' mimetype='image/png' paramId='signData'/>"
            "</fields></word-document>"
        )
        with self.assertRaisesRegex(WordConfigTextUpdateError, "image_field_not_text"):
            build_word_config_text_updates(parsed, {0: "Logo"})
        with self.assertRaisesRegex(WordConfigTextUpdateError, "external_parameter"):
            build_word_config_text_updates(parsed, {1: "Signature"})

    def test_rejects_non_text_mime_and_invalid_indices(self):
        parsed = config(
            "<word-document><fields>"
            "<field id='Binary' mimetype='application/octet-stream'>abc</field>"
            "</fields></word-document>"
        )
        with self.assertRaisesRegex(WordConfigTextUpdateError, "unsupported_text_field_mimetype"):
            build_word_config_text_updates(parsed, {0: "Binary"})
        for index in (True, -1, 1, "0"):
            with self.subTest(index=index), self.assertRaises(WordConfigTextUpdateError):
                build_word_config_text_updates(parsed, {index: "Target"})

    def test_rejects_duplicate_casefold_targets_and_bad_names(self):
        parsed = config(
            "<word-document><fields>"
            "<field id='A'>one</field><field id='B'>two</field>"
            "</fields></word-document>"
        )
        with self.assertRaisesRegex(WordConfigTextUpdateError, "duplicate_target"):
            build_word_config_text_updates(parsed, {0: "Target", 1: "target"})
        for target in ("", " Target", "Target "):
            with self.subTest(target=target), self.assertRaises(WordConfigTextUpdateError):
                build_word_config_text_updates(parsed, {0: target})

    def test_empty_mapping_is_noop_and_mapping_is_immutable(self):
        parsed = config("<word-document><fields><field id='A'>x</field></fields></word-document>")
        updates = build_word_config_text_updates(parsed, {})
        mapping = as_custom_property_update_mapping(updates)
        self.assertEqual(dict(mapping), {})
        with self.assertRaises(TypeError):
            mapping["x"] = "y"


if __name__ == "__main__":
    unittest.main()
