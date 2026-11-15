import unittest

from emwat_linux.protocol import ProtocolError, parse_method_call


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

    def test_rejects_non_bytes(self):
        with self.assertRaises(TypeError):
            parse_method_call("<emwat/>")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
