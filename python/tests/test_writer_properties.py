import unittest

from emwat_linux.writer_properties import (
    WriterPropertyUpdateError,
    set_custom_document_property,
)


class FakePropertyInfo:
    def __init__(self, names):
        self.names = set(names)

    def hasPropertyByName(self, name):
        return name in self.names


class FakeUserProperties:
    def __init__(self):
        self.values = {"LetterSubject": "old"}
        self.info = FakePropertyInfo(self.values)

    def getPropertySetInfo(self):
        return self.info

    def setPropertyValue(self, name, value):
        if name not in self.values:
            raise KeyError(name)
        self.values[name] = value

    def getPropertyValue(self, name):
        return self.values[name]


class FakeDocument:
    def __init__(self):
        self.properties = FakeUserProperties()

    def getDocumentProperties(self):
        return type(
            "DocumentProperties",
            (),
            {"getUserDefinedProperties": lambda _self: self.properties},
        )()


class WriterPropertyUpdateTests(unittest.TestCase):
    def test_updates_only_an_existing_exact_property(self):
        document = FakeDocument()
        set_custom_document_property(document, "LetterSubject", "new subject")
        self.assertEqual(
            document.properties.getPropertyValue("LetterSubject"),
            "new subject",
        )

    def test_does_not_create_an_unknown_property(self):
        document = FakeDocument()
        with self.assertRaisesRegex(KeyError, "custom_property_not_found"):
            set_custom_document_property(document, "UnknownField", "value")
        self.assertNotIn("UnknownField", document.properties.values)

    def test_rejects_empty_property_name(self):
        with self.assertRaisesRegex(ValueError, "custom_property_name_required"):
            set_custom_document_property(FakeDocument(), "", "value")

    def test_wraps_unexpected_uno_update_errors(self):
        class BrokenProperties(FakeUserProperties):
            def setPropertyValue(self, _name, _value):
                raise RuntimeError("UNO failure")

        document = FakeDocument()
        document.properties = BrokenProperties()
        with self.assertRaises(WriterPropertyUpdateError):
            set_custom_document_property(document, "LetterSubject", "new")


if __name__ == "__main__":
    unittest.main()
