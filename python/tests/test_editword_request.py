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
        return MethodCall(
            class_name="EditWordDocument",
            params=MappingProxyType(params),
            version="1.0",
        )

    def test_decodes_document_and_inner_config_but_preserves_sign_data(self):
        config_xml = (
            b'<word-document status="edit">'
            b'<permission allowSave="true"/>'
            b'<fields><field id="LetterSubject" encryption="urlencoded">A%20B</field></fields>'
            b'</word-document>'
        )
        doc_bytes = bytes.fromhex("d0cf11e0a1b11ae1") + b"synthetic-doc"
        call = self.make_call(
            wordConfig=b64(config_xml),
            wordBody=b64(doc_bytes),
            signData="one%26two&three",
            customFlag="opaque",
        )
        request = parse_editword_request(call)
        self.assertEqual(request.config.root_attributes["status"], "edit")
        self.assertEqual(request.config.fields[0].text, "A%20B")
        self.assertEqual(request.document_bytes, doc_bytes)
        self.assertEqual(request.sign_data_text, "one%26two&three")
        self.assertEqual(request.extra_parameters["customFlag"], "opaque")

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
            parse_editword_request(
                self.make_call(wordConfig=config, wordBody=body),
                max_encoded_document_chars=4,
            )
        with self.assertRaises(EditWordDocumentRequestError):
            parse_editword_request(
                self.make_call(wordConfig=config, wordBody=body),
                max_document_bytes=4,
            )

    def test_wraps_invalid_inner_config(self):
        with self.assertRaises(EditWordDocumentRequestError):
            parse_editword_request(
                self.make_call(wordConfig="not-base64", wordBody=b64(b"doc"))
            )


if __name__ == "__main__":
    unittest.main()
