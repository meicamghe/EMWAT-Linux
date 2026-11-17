import base64
import unittest

from emwat_linux.editword_request import EditWordDocumentRequest
from emwat_linux.payload_inventory import inspect_request_payloads
from emwat_linux.word_config import parse_word_config


def request(fields, sign_data="opaque-signature-data"):
    xml = (
        "<word-document><fields>"
        + "".join(fields)
        + "</fields></word-document>"
    ).encode()
    return EditWordDocumentRequest(
        config=parse_word_config(base64.b64encode(xml).decode()),
        document_bytes=b"synthetic-document",
        sign_data_text=sign_data,
        extra_parameters={},
    )


class PayloadInventoryTests(unittest.TestCase):
    def test_reports_binary_image_size_and_hash_without_returning_bytes(self):
        payload = b"synthetic-png-payload"
        encoded = base64.b64encode(payload).decode()
        report = inspect_request_payloads(
            request([
                f'<field id="logo" mimetype="image/png" encryption="base64">{encoded}</field>'
            ])
        )
        self.assertEqual(report.decoded_field_count, 1)
        self.assertEqual(len(report.image_payloads), 1)
        self.assertEqual(report.image_payloads[0].field_id, "logo")
        self.assertEqual(report.image_payloads[0].mimetype, "image/png")
        self.assertEqual(report.image_payloads[0].byte_count, len(payload))
        self.assertEqual(len(report.image_payloads[0].sha256), 64)
        self.assertEqual(report.external_references, ())

    def test_keeps_sign_data_opaque_and_reports_external_ids(self):
        report = inspect_request_payloads(
            request([
                '<field id="signature" paramId="sig-01" mimetype="image/png" encryption="base64">'
                + base64.b64encode(b"not-external-data").decode()
                + "</field>"
            ])
        )
        self.assertEqual(
            [(item.field_id, item.parameter_id) for item in report.external_references],
            [("signature", "sig-01")],
        )
        self.assertEqual(report.unresolved_external_references, ("sig-01",))
        self.assertTrue(report.sign_data_present)
        self.assertEqual(report.sign_data_character_count, len("opaque-signature-data"))
        self.assertEqual(len(report.sign_data_sha256 or ""), 64)

    def test_decodes_optional_attributes_using_their_own_encoding(self):
        value = "سلام"
        encoded = base64.b64encode(value.encode()).decode()
        xml = (
            "<word-document><optional-attributes>"
            '<attribute id="department" type="text"><content encryption="base64">'
            + encoded
            + "</content></attribute>"
            "</optional-attributes></word-document>"
        ).encode()
        req = EditWordDocumentRequest(
            config=parse_word_config(base64.b64encode(xml).decode()),
            document_bytes=b"synthetic-document",
            sign_data_text="",
            extra_parameters={},
        )
        report = inspect_request_payloads(req)
        self.assertEqual(len(report.optional_attributes), 1)
        self.assertEqual(report.optional_attributes[0].attribute_id, "department")
        self.assertEqual(report.optional_attributes[0].value_type, "text")
        self.assertEqual(report.optional_attributes[0].character_count, len(value))
        self.assertEqual(len(report.optional_attributes[0].sha256), 64)

    def test_rejects_binary_optional_attribute_in_text_inventory(self):
        encoded = base64.b64encode(b"\xff\xfe").decode()
        xml = (
            "<word-document><optional-attributes>"
            '<attribute id="opaque"><content encryption="base64">'
            + encoded
            + "</content></attribute>"
            "</optional-attributes></word-document>"
        ).encode()
        req = EditWordDocumentRequest(
            config=parse_word_config(base64.b64encode(xml).decode()),
            document_bytes=b"synthetic-document",
            sign_data_text="",
            extra_parameters={},
        )
        with self.assertRaisesRegex(ValueError, "optional_attribute_must_be_text"):
            inspect_request_payloads(req)

    def test_empty_sign_data_has_no_digest(self):
        report = inspect_request_payloads(request([], sign_data=""))
        self.assertFalse(report.sign_data_present)
        self.assertEqual(report.sign_data_character_count, 0)
        self.assertIsNone(report.sign_data_sha256)

    def test_rejects_image_declared_as_text_instead_of_binary(self):
        with self.assertRaisesRegex(ValueError, "image_payload_not_binary"):
            inspect_request_payloads(
                request(['<field id="logo" mimetype="image/png">not-binary</field>'])
            )

    def test_rejects_unknown_field_encoding_instead_of_guessing(self):
        with self.assertRaisesRegex(ValueError, "unsupported_field_encoding"):
            inspect_request_payloads(
                request(['<field id="logo" mimetype="image/png" encryption="mystery">abc</field>'])
            )


if __name__ == "__main__":
    unittest.main()
