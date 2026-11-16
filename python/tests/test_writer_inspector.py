import unittest

from emwat_linux.writer_inspector import inspect_writer_document


class FakeContainer:
    def __init__(self, names):
        self.names = names

    def getElementNames(self):
        return self.names


class FakeEnumeration:
    def __init__(self, values):
        self.values = iter(values)

    def hasMoreElements(self):
        if not hasattr(self, "_next"):
            self._next = next(self.values, None)
        return self._next is not None

    def nextElement(self):
        value = self._next
        del self._next
        return value


class FakeFields:
    def createEnumeration(self):
        return FakeEnumeration([FakeField()])


class FakeField:
    def getImplementationName(self):
        return "com.sun.star.text.TextField.DateTime"

    def getPresentation(self, _show_command):
        raise AssertionError("field values must not be read by the inspector")

    def getPropertySetInfo(self):
        return type(
            "PropertyInfo",
            (),
            {
                "getProperties": lambda _self: [
                    type("Property", (), {"Name": "IsDate"})(),
                    type("Property", (), {"Name": "IsFixed"})(),
                ]
            },
        )()


class FakeUserDefinedProperties:
    def getPropertySetInfo(self):
        return type("PropertyInfo", (), {
            "getProperties": lambda _self: [
                type("Property", (), {"Name": "EMWATLetterNumber"})(),
                type("Property", (), {"Name": "EMWATSubject"})(),
            ]
        })()

    def getPropertyValue(self, _name):
        raise AssertionError("custom property values must not be read")


class FakeDocumentProperties:
    def getUserDefinedProperties(self):
        return FakeUserDefinedProperties()


class FakeDocument:
    def getBookmarks(self):
        return FakeContainer(["LetterSubject", "LetterNumber"])

    def getNamedRanges(self):
        return FakeContainer(["NamedRangeA"])

    def getTextSections(self):
        return FakeContainer([])

    def getTextTables(self):
        return FakeContainer(["Table1"])

    def getTextFrames(self):
        return FakeContainer([])

    def getGraphicObjects(self):
        return FakeContainer(["Image1"])

    def getDocumentIndexes(self):
        return FakeContainer([])

    def getTextFields(self):
        return FakeFields()

    def getDocumentProperties(self):
        return FakeDocumentProperties()


class WriterInspectorTests(unittest.TestCase):
    def test_returns_sorted_structural_metadata_without_document_text(self):
        catalog = inspect_writer_document(FakeDocument())
        self.assertEqual(catalog.bookmarks, ("LetterNumber", "LetterSubject"))
        self.assertEqual(catalog.named_ranges, ("NamedRangeA",))
        self.assertEqual(catalog.text_tables, ("Table1",))
        self.assertEqual(catalog.graphic_objects, ("Image1",))
        self.assertEqual(len(catalog.text_fields), 1)
        self.assertEqual(
            catalog.text_fields[0].implementation_name,
            "com.sun.star.text.TextField.DateTime",
        )
        self.assertEqual(catalog.text_fields[0].property_names, ("IsDate", "IsFixed"))
        self.assertEqual(
            catalog.custom_document_properties,
            ("EMWATLetterNumber", "EMWATSubject"),
        )


if __name__ == "__main__":
    unittest.main()
