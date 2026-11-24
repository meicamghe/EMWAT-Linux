import base64
from pathlib import Path
import tempfile
import unittest

from emwat_linux.word_assets import (
    WriterAssetMappingError,
    WriterGraphicUpdate,
    apply_writer_graphic_updates,
    build_writer_graphic_updates,
    inspect_word_assets,
)
from emwat_linux.word_config import parse_word_config


def config(xml):
    return parse_word_config(base64.b64encode(xml.encode()).decode())


class FakeGraphic:
    def __init__(self, url):
        self.url = url
        self.calls = 0

    def getPropertyValue(self, name):
        if name != "GraphicURL":
            raise KeyError(name)
        return self.url

    def setPropertyValue(self, name, value):
        if name != "GraphicURL":
            raise KeyError(name)
        self.calls += 1
        self.url = value


class FakeGraphicContainer:
    def __init__(self, values):
        self.values = values

    def getElementNames(self):
        return tuple(self.values)

    def getByName(self, name):
        return self.values[name]


class FakeDocument:
    def __init__(self, values):
        self.graphics = FakeGraphicContainer(values)

    def getGraphicObjects(self):
        return self.graphics


class WordAssetMappingTests(unittest.TestCase):
    def test_extracts_image_bytes_and_all_twenty_signer_slots(self):
        xml = (
            "<word-document><fields>"
            "<field id='LetterSignerPer0' encryption='urlencoded'>A%20B</field>"
            "<field id='LetterSignerDep0'>Dept</field>"
            "<field id='LetterSignerUnit19'>Unit</field>"
            "<field id='LetterSignerIndexUnit0'>Index unit</field>"
            "<field id='SignNumberOfSigner0'>7</field>"
            "<field id='BehalfNameOfSigner0'>For another</field>"
            "<field id='SignOfSignerStart19&#8224;SignOfSignerEnd19' mimetype='image/png' encryption='base64'>AQID</field>"
            "<field id='SenderSignature' mimetype='image/png' encryption='base64'>BAUG</field>"
            "<field id='EmptySignature' mimetype='image/tif' encryption='base64'/>"
            "</fields></word-document>"
        )
        inventory = inspect_word_assets(config(xml))
        self.assertEqual(inventory.signer_slot_count, 2)
        self.assertEqual(len(inventory.signer_slots), 20)
        self.assertEqual(inventory.signer_slots[0].person, "A B")
        self.assertEqual(inventory.signer_slots[0].department, "Dept")
        self.assertEqual(inventory.signer_slots[19].unit, "Unit")
        self.assertEqual(inventory.signer_slots[1].person, "")
        self.assertEqual(inventory.images[0].data, b"\x01\x02\x03")
        self.assertEqual(inventory.images[0].mimetype, "image/png")
        self.assertEqual(inventory.images[1].mimetype, "image/tif")
        self.assertEqual(inventory.empty_image_field_indices, (4,))

    def test_rejects_duplicate_signer_slot_members(self):
        with self.assertRaisesRegex(WriterAssetMappingError, "duplicate_signer_metadata_field"):
            inspect_word_assets(config(
                "<word-document><fields>"
                "<field id='LetterSignerPer0'>A</field>"
                "<field id='LetterSignerPer0'>B</field>"
                "</fields></word-document>"
            ))

    def test_rejects_signature_twin_field_without_image_mime(self):
        with self.assertRaisesRegex(WriterAssetMappingError, "signer_signature_field_not_image"):
            inspect_word_assets(config(
                "<word-document><fields>"
                "<field id='SignOfSignerStart0&#8224;SignOfSignerEnd0'>not-image</field>"
                "</fields></word-document>"
            ))

    def test_rejects_unsupported_image_mime_and_non_base64_image(self):
        cases = (
            "<field id='x' mimetype='image/webp' encryption='base64'>AQID</field>",
            "<field id='x' mimetype='image/png'>AQID</field>",
        )
        for field in cases:
            with self.subTest(field=field), self.assertRaises(WriterAssetMappingError):
                inspect_word_assets(config(f"<word-document><fields>{field}</fields></word-document>"))

    def test_builds_updates_by_stable_field_index_not_duplicate_field_id(self):
        inventory = inspect_word_assets(config(
            "<word-document><fields>"
            "<field id='Signature' mimetype='image/png' encryption='base64'>AQID</field>"
            "<field id='Signature' mimetype='image/png' encryption='base64'>BAUG</field>"
            "</fields></word-document>"
        ))
        updates = build_writer_graphic_updates(inventory, {0: "SignatureA", 1: "SignatureB"})
        self.assertEqual([item.target_name for item in updates], ["SignatureA", "SignatureB"])
        self.assertEqual([item.data for item in updates], [b"\x01\x02\x03", b"\x04\x05\x06"])

    def test_refuses_implicit_or_ambiguous_targets(self):
        inventory = inspect_word_assets(config(
            "<word-document><fields>"
            "<field id='Sig0' mimetype='image/png' encryption='base64'>AQID</field>"
            "<field id='Sig1' mimetype='image/png' encryption='base64'>BAUG</field>"
            "</fields></word-document>"
        ))
        with self.assertRaisesRegex(WriterAssetMappingError, "duplicate_writer_graphic_target"):
            build_writer_graphic_updates(inventory, {0: "Same", 1: "Same"})
        with self.assertRaisesRegex(WriterAssetMappingError, "unknown_field"):
            build_writer_graphic_updates(inventory, {9: "Unknown"})
        empty = inspect_word_assets(config(
            "<word-document><fields><field id='Sig' mimetype='image/png' encryption='base64'/></fields></word-document>"
        ))
        with self.assertRaisesRegex(WriterAssetMappingError, "empty_image_field_not_applied"):
            build_writer_graphic_updates(empty, {0: "Sig"})

    def test_applies_existing_graphics_and_keeps_frame_properties(self):
        document = FakeDocument({"sig": FakeGraphic("file:///old.png")})
        update = WriterGraphicUpdate(0, "Signature", "sig", "image/png", b"\x89PNG")
        with tempfile.TemporaryDirectory() as tmp:
            result = apply_writer_graphic_updates(document, (update,), Path(tmp))
            self.assertEqual(result, ("sig",))
            graphic = document.graphics.values["sig"]
            self.assertTrue(graphic.url.endswith("emwat-image-0.png"))
            self.assertEqual(graphic.calls, 1)

    def test_validates_all_targets_before_mutation(self):
        document = FakeDocument({"sig": FakeGraphic("file:///old.png")})
        updates = (
            WriterGraphicUpdate(0, "Signature", "sig", "image/png", b"\x89PNG"),
            WriterGraphicUpdate(1, "QR", "missing", "image/png", b"\x89PNG"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(KeyError, "writer_graphic_object_not_found"):
                apply_writer_graphic_updates(document, updates, Path(tmp))
        self.assertEqual(document.graphics.values["sig"].url, "file:///old.png")

    def test_rolls_back_prior_graphics_when_later_setter_fails(self):
        class FailsOnSecond(FakeGraphic):
            def setPropertyValue(self, name, value):
                if value.startswith("file:") and "image-1" in value:
                    raise RuntimeError("UNO setter failed")
                super().setPropertyValue(name, value)

        document = FakeDocument({
            "one": FakeGraphic("file:///old-one.png"),
            "two": FailsOnSecond("file:///old-two.png"),
        })
        updates = (
            WriterGraphicUpdate(0, "Sig0", "one", "image/png", b"\x89PNG"),
            WriterGraphicUpdate(1, "Sig1", "two", "image/png", b"\x89PNG"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(WriterAssetMappingError, "update_failed"):
                apply_writer_graphic_updates(document, updates, Path(tmp))
        self.assertEqual(document.graphics.values["one"].url, "file:///old-one.png")
        self.assertEqual(document.graphics.values["two"].url, "file:///old-two.png")

    def test_rejects_incomplete_rollback(self):
        class BrokenGraphic(FakeGraphic):
            def setPropertyValue(self, name, value):
                if value.startswith("file:"):
                    raise RuntimeError("setter failure")
                raise RuntimeError("rollback failure")

        document = FakeDocument({"sig": BrokenGraphic("file:///old.png")})
        update = WriterGraphicUpdate(0, "Sig", "sig", "image/png", b"\x89PNG")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(WriterAssetMappingError, "rollback_incomplete"):
                apply_writer_graphic_updates(document, (update,), Path(tmp))


if __name__ == "__main__":
    unittest.main()
