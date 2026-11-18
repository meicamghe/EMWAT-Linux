import base64
import unittest
import xml.etree.ElementTree as ET

from emwat_linux.protocol import (
    WORD_RESPONSE_CONTENT_TYPE,
    ProtocolError,
    parse_method_call,
    serialize_word_document_response,
)


class MethodEnvelopeTests(unittest.TestCase):
    def test_parses_confirmed_envelope_and_preserves_parameter_text(self):
        payload = (
            b'<?xml version="1.0" encoding="utf-8"?>'
            b'<emwat version="1.0"><method class="EditWordDocument">'
            b'<param name="wordConfig">  PHdvcmQtZG9jdW1lbnQvPg==  </param>'
            b'<param name="wordBody"><![CDATA[body & text]]></param>'
            b'</method></emwat>'
        )
        call = parse_method_call(payload)
        self.assertEqual(call.class_name, "EditWordDocument")
        self.assertEqual(call.version, "1.0")
        self.assertEqual(call.params["wordConfig"], "  PHdvcmQtZG9jdW1lbnQvPg==  ")
        self.assertEqual(call.params["wordBody"], "body & text")

    def test_does_not_restrict_unknown_class_names(self):
        call = parse_method_call(
            b'<emwat version="1.0"><method class="FutureMethod">'
            b'<param name="x">1</param></method></emwat>'
        )
        self.assertEqual(call.class_name, "FutureMethod")

    def test_rejects_wrong_root_or_version(self):
        cases = [
            b'<other version="1.0"><method class="X"/></other>',
            b'<emwat version="2.0"><method class="X"/></emwat>',
        ]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ProtocolError):
                parse_method_call(payload)

    def test_rejects_multiple_methods_and_unknown_children(self):
        cases = [
            b'<emwat version="1.0"><method class="X"/><method class="Y"/></emwat>',
            b'<emwat version="1.0"><method class="X"><other/></method></emwat>',
        ]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ProtocolError):
                parse_method_call(payload)

    def test_rejects_duplicate_or_invalid_parameter_names(self):
        cases = [
            b'<emwat version="1.0"><method class="X"><param name="a"/>'
            b'<param name="a"/></method></emwat>',
            b'<emwat version="1.0"><method class="X"><param name=" a "/>'
            b'</method></emwat>',
        ]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ProtocolError):
                parse_method_call(payload)

    def test_rejects_dtd_entities_and_nested_parameter_markup(self):
        cases = [
            b'<!DOCTYPE emwat [<!ENTITY x "boom">]><emwat version="1.0">'
            b'<method class="X"/></emwat>',
            b'<emwat version="1.0"><method class="X">'
            b'<param name="x"><inner/></param></method></emwat>',
        ]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ProtocolError):
                parse_method_call(payload)

    def test_rejects_invalid_encoding_and_size(self):
        with self.assertRaises(ProtocolError):
            parse_method_call(b"\xff")
        with self.assertRaises(ProtocolError):
            parse_method_call(b"<emwat version='1.0'/>", max_bytes=4)

    def test_all_parser_and_serializer_limits_require_positive_builtin_integers(self):
        invalid_values = (True, False, 1.5, 16.0, "16", 0, -1, None)
        payload = b'<emwat version="1.0"><method class="X"/></emwat>'
        for value in invalid_values:
            with self.subTest(parser_limit=value), self.assertRaisesRegex(
                ValueError, "max_bytes must be a positive integer"
            ):
                parse_method_call(payload, max_bytes=value)
            with self.subTest(serializer_limit=value), self.assertRaisesRegex(
                ValueError, "max_response_bytes must be a positive integer"
            ):
                serialize_word_document_response(b"doc", max_response_bytes=value)

    def test_preserves_capture_sized_opaque_document_payload(self):
        # The captured EditWordDocument request carried a >1 MB Base64 wordBody.
        # Keep this synthetic: no captured customer document enters the test suite.
        opaque = b"AQID" * 300_000
        payload = (
            b'<emwat version="1.0"><method class="EditWordDocument">'
            b'<param name="wordBody">' + opaque +
            b'</param></method></emwat>'
        )
        call = parse_method_call(payload, max_bytes=2 * 1024 * 1024)
        self.assertEqual(len(call.params["wordBody"]), len(opaque))
        self.assertEqual(call.params["wordBody"][:16], "AQID" * 4)
        self.assertEqual(call.params["wordBody"][-16:], "AQID" * 4)

    def test_serializes_observed_word_document_response(self):
        document = bytes.fromhex("d0cf11e0a1b11ae1") + b"synthetic-word-bytes"
        response = serialize_word_document_response(document)
        root = ET.fromstring(response)
        self.assertEqual(root.tag, "response-word")
        self.assertEqual(root.attrib, {"status": "success"})
        node = root.find("./return-types/type")
        self.assertIsNotNone(node)
        self.assertEqual(node.attrib, {
            "mimetype": "application/msword",
            "encryption": "base64",
        })
        self.assertEqual(base64.b64decode(node.text, validate=True), document)
        self.assertEqual(
            WORD_RESPONSE_CONTENT_TYPE,
            "text/html; charset=ISO-8859-1",
        )

    def test_word_response_serializer_enforces_size_and_input_type(self):
        with self.assertRaises(ProtocolError):
            serialize_word_document_response(b"document", max_response_bytes=8)
        with self.assertRaises(ProtocolError):
            serialize_word_document_response(b"")
        with self.assertRaises(TypeError):
            serialize_word_document_response("not bytes")  # type: ignore[arg-type]

    def test_word_response_size_is_rejected_before_base64_expansion(self):
        document = b"x" * (1024 * 1024)
        with self.assertRaisesRegex(ProtocolError, "response_size_invalid"):
            serialize_word_document_response(document, max_response_bytes=1024)

    def test_rejects_non_bytes(self):
        with self.assertRaises(TypeError):
            parse_method_call("<emwat/>")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
