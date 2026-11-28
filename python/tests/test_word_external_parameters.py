import base64
import unittest

from emwat_linux.word_config import parse_word_config
from emwat_linux.word_external_parameters import (
    ExternalParameterResolutionError,
    resolve_external_parameter_bindings,
)


def config(xml: str):
    return parse_word_config(base64.b64encode(xml.encode("utf-8")).decode("ascii"))


class ExternalParameterBindingTests(unittest.TestCase):
    def test_resolves_sign_data_exactly_and_keeps_delimiter_attributes_distinct(self):
        parsed = config(
            "<word-document><fields>"
            "<field id='SignsStart&#8224;SignsEnd' paramId='signData' "
            "mimetype='image/png' encryption='base64' separator='&amp;' "
            "concater='\\\\n' concator='\\\\r'/>"
            "<field id='LetterSignerPer0' encryption='unsupported'>Signer</field>"
            "</fields></word-document>"
        )
        opaque = "one%26two&three+four\\nEND"
        result = resolve_external_parameter_bindings(parsed, {"signData": opaque})
        self.assertEqual(len(result), 1)
        item = result[0]
        self.assertEqual(item.field_index, 0)
        self.assertEqual(item.field_id, "SignsStart†SignsEnd")
        self.assertEqual(item.parameter_id, "signData")
        self.assertTrue(item.present)
        self.assertEqual(item.raw_value, opaque)
        self.assertEqual(item.mimetype, "image/png")
        self.assertEqual(item.encryption, "base64")
        self.assertEqual(item.separator, "&")
        self.assertEqual(item.concater, "\\\\n")
        self.assertEqual(item.concator, "\\\\r")
        self.assertNotIn(opaque, repr(item))

    def test_distinguishes_missing_parameter_from_present_empty_parameter(self):
        parsed = config(
            "<word-document><fields>"
            "<field id='ExternalA' paramId='signData' mimetype='image/png'/>"
            "<field id='ExternalB' paramId='letterImages' mimetype='image/png'/>"
            "</fields></word-document>"
        )
        present_empty, missing = resolve_external_parameter_bindings(parsed, {"signData": ""})
        self.assertTrue(present_empty.present)
        self.assertEqual(present_empty.raw_value, "")
        self.assertFalse(missing.present)
        self.assertEqual(missing.raw_value, "")

    def test_repeated_references_preserve_order_and_count_payload_once(self):
        parsed = config(
            "<word-document><fields>"
            "<field id='A' paramId='signData'/><field id='B' paramId='signData'/>"
            "</fields></word-document>"
        )
        result = resolve_external_parameter_bindings(
            parsed, {"signData": "opaque"}, max_total_parameter_chars=6
        )
        self.assertEqual([item.field_id for item in result], ["A", "B"])
        self.assertEqual([item.field_index for item in result], [0, 1])

    def test_enforces_per_value_and_total_bounds(self):
        parsed = config(
            "<word-document><fields>"
            "<field id='A' paramId='a'/><field id='B' paramId='b'/>"
            "</fields></word-document>"
        )
        with self.assertRaisesRegex(ExternalParameterResolutionError, "external_parameter_size_exceeded"):
            resolve_external_parameter_bindings(parsed, {"a": "123"}, max_parameter_chars=2)
        with self.assertRaisesRegex(ExternalParameterResolutionError, "total_external_parameter_size_exceeded"):
            resolve_external_parameter_bindings(
                parsed, {"a": "12", "b": "34"},
                max_parameter_chars=4, max_total_parameter_chars=3,
            )

    def test_rejects_non_text_outer_parameters(self):
        parsed = config("<word-document><fields><field id='A' paramId='signData'/></fields></word-document>")
        with self.assertRaisesRegex(ExternalParameterResolutionError, "outer_parameters_must_be_text"):
            resolve_external_parameter_bindings(parsed, {"signData": b"binary"})


if __name__ == "__main__":
    unittest.main()
