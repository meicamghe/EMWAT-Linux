import base64
import unittest
from types import MappingProxyType

from emwat_linux.editword_request import (
    EditWordDocumentRequestError,
    parse_editword_request,
)
from emwat_linux.protocol import MethodCall


def b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


class EditWordDocumentRequestTests(unittest.TestCase):
    def make_call(self, **params):
        return MethodCall("EditWordDocument", MappingProxyType(params), "1.0")

    def test_decodes_document_and_inner_config_but_preserves_sign_data(self):
        config_xml = (
            b'<word-document status="edit">'
            b'<permission allowSave="true"/>'
            b'<fields><field id="LetterSubject" encryption="urlencoded">A%20B</field></fields>'
            b'</word-document>'
        )
        doc_bytes = bytes.fromhex("d0cf11e0a1b11ae1") + b"synthetic-doc"
        request = parse_editword_request(self.make_call(
            wordConfig=b64(config_xml), wordBody=b64(doc_bytes),
            signData="one%26two&three", customFlag="opaque",
        ))
        self.assertEqual(request.config.root_attributes["status"], "edit")
        self.assertEqual(request.config.fields[0].text, "A%20B")
        self.assertEqual(request.document_bytes, doc_bytes)
        self.assertEqual(request.sign_data_text, "one%26two&three")
        self.assertEqual(request.extra_parameters["customFlag"], "opaque")

    def test_request_repr_does_not_expose_document_or_auxiliary_payloads(self):
        secret = "PRIVATE_SIGN_DATA_MARKER"
        request = parse_editword_request(self.make_call(
            wordConfig=b64(b"<word-document/>"),
            wordBody=b64(bytes.fromhex("d0cf11e0a1b11ae1") + b"private"),
            signData=secret,
            letterImages="PRIVATE_LETTER_IMAGES_MARKER",
        ))
        rendered = repr(request)
        self.assertNotIn(secret, rendered)
        self.assertNotIn("PRIVATE_LETTER_IMAGES_MARKER", rendered)
        self.assertNotIn("private", rendered)

    def test_enforces_auxiliary_parameter_size_limits(self):
        args = dict(wordConfig=b64(b"<word-document/>"), wordBody=b64(b"doc"))
        with self.assertRaisesRegex(EditWordDocumentRequestError, "sign_data_size_exceeded"):
            parse_editword_request(self.make_call(**args, signData="1234"), max_auxiliary_parameter_chars=3)
        with self.assertRaisesRegex(EditWordDocumentRequestError, "extra_parameter_size_exceeded"):
            parse_editword_request(self.make_call(**args, letterImages="1234"), max_auxiliary_parameter_chars=3)

    def test_rejects_wrong_class_and_missing_required_parameters(self):
        wrong = MethodCall("OtherMethod", MappingProxyType({}), "1.0")
        with self.assertRaises(EditWordDocumentRequestError):
            parse_editword_request(wrong)
        with self.assertRaises(EditWordDocumentRequestError):
            parse_editword_request(self.make_call(wordConfig=b64(b"<word-document/>")))

    def test_rejects_invalid_document_base64_and_empty_document(self):
        config = b64(b"<word-document/>")
        for body in ("%%%invalid%%%", ""):
            with self.subTest(body=body), self.assertRaises(EditWordDocumentRequestError):
                parse_editword_request(self.make_call(wordConfig=config, wordBody=body))
        with self.assertRaises(EditWordDocumentRequestError):
            parse_editword_request(self.make_call(wordConfig=config, wordBody=b64(b"")))

    def test_enforces_encoded_and_decoded_document_limits(self):
        config = b64(b"<word-document/>")
        body = b64(b"document")
        with self.assertRaises(EditWordDocumentRequestError):
            parse_editword_request(self.make_call(wordConfig=config, wordBody=body), max_encoded_document_chars=4)
        with self.assertRaises(EditWordDocumentRequestError):
            parse_editword_request(self.make_call(wordConfig=config, wordBody=body), max_document_bytes=4)

    def test_enforces_encoded_config_limit_before_base64_decode(self):
        config = b64(b"<word-document/>")
        body = b64(b"document")
        with self.assertRaisesRegex(EditWordDocumentRequestError, "word_config_invalid"):
            parse_editword_request(self.make_call(wordConfig=config, wordBody=body), max_encoded_config_chars=len(config) - 1)

    def test_all_size_limits_require_positive_builtin_integers(self):
        config = b64(b"<word-document/>")
        body = b64(b"document")
        invalid_values = (True, False, 1.5, 16.0, "16", 0, -1, None)
        for parameter in (
            "max_document_bytes", "max_encoded_document_chars", "max_config_bytes",
            "max_encoded_config_chars", "max_auxiliary_parameter_chars",
        ):
            for value in invalid_values:
                with self.subTest(parameter=parameter, value=value):
                    with self.assertRaisesRegex(ValueError, "size limits must be positive integers"):
                        parse_editword_request(
                            self.make_call(wordConfig=config, wordBody=body),
                            **{parameter: value},
                        )

    def test_rejects_non_text_protocol_parameters_cleanly(self):
        config = b64(b"<word-document/>")
        body = b64(b"document")
        cases = (
            ({"wordConfig": 7, "wordBody": body}, "word_config_invalid_type"),
            ({"wordConfig": config, "wordBody": b"not-text"}, "word_body_invalid_type"),
            ({"wordConfig": config, "wordBody": body, "signData": None}, "sign_data_invalid_type"),
            ({"wordConfig": config, "wordBody": body, "extra": 9}, "extra_parameter_invalid_type"),
        )
        for params, error in cases:
            with self.subTest(error=error), self.assertRaisesRegex(EditWordDocumentRequestError, error):
                parse_editword_request(MethodCall("EditWordDocument", params, "1.0"))

    def test_rejects_invalid_method_call_and_parameter_container(self):
        for call in (None, object(), MethodCall("EditWordDocument", None, "1.0")):
            with self.subTest(call=call), self.assertRaises(EditWordDocumentRequestError):
                parse_editword_request(call)

    def test_wraps_invalid_inner_config(self):
        with self.assertRaises(EditWordDocumentRequestError):
            parse_editword_request(self.make_call(wordConfig="not-base64", wordBody=b64(b"doc")))


if __name__ == "__main__":
    unittest.main()
