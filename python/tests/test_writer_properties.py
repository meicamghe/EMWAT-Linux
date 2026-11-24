import unittest

from emwat_linux.writer_properties import (
    WriterPropertyUpdateError,
    set_custom_document_properties,
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

    def test_batch_validates_all_names_before_mutating(self):
        document = FakeDocument()
        with self.assertRaisesRegex(KeyError, "custom_property_not_found"):
            set_custom_document_properties(
                document,
                {"LetterSubject": "new", "UnknownField": "value"},
            )
        self.assertEqual(
            document.properties.getPropertyValue("LetterSubject"),
            "old",
        )
        self.assertNotIn("UnknownField", document.properties.values)

    def test_batch_updates_multiple_existing_properties(self):
        document = FakeDocument()
        document.properties.values["LetterNumber"] = "old-number"
        document.properties.info = FakePropertyInfo(document.properties.values)
        set_custom_document_properties(
            document,
            {"LetterSubject": "new", "LetterNumber": "42"},
        )
        self.assertEqual(document.properties.values["LetterSubject"], "new")
        self.assertEqual(document.properties.values["LetterNumber"], "42")

    def test_batch_rolls_back_prior_properties_when_later_update_fails(self):
        class FailsOnSecondProperty(FakeUserProperties):
            def setPropertyValue(self, name, value):
                if name == "LetterNumber":
                    raise RuntimeError("UNO failure")
                super().setPropertyValue(name, value)

        document = FakeDocument()
        document.properties = FailsOnSecondProperty()
        document.properties.values["LetterNumber"] = "old-number"
        document.properties.info = FakePropertyInfo(document.properties.values)

        with self.assertRaises(WriterPropertyUpdateError):
            set_custom_document_properties(
                document,
                {"LetterSubject": "new", "LetterNumber": "new-number"},
            )

        self.assertEqual(
            document.properties.getPropertyValue("LetterSubject"), "old"
        )
        self.assertEqual(
            document.properties.getPropertyValue("LetterNumber"), "old-number"
        )

    def test_rolls_back_a_property_that_mutates_before_raising(self):
        class MutatesThenFails(FakeUserProperties):
            def setPropertyValue(self, name, value):
                if name == "LetterNumber" and value == "new-number":
                    self.values[name] = value
                    raise RuntimeError("UNO setter failed after mutation")
                super().setPropertyValue(name, value)

        document = FakeDocument()
        document.properties = MutatesThenFails()
        document.properties.values["LetterNumber"] = "old-number"
        document.properties.info = FakePropertyInfo(document.properties.values)

        with self.assertRaises(WriterPropertyUpdateError):
            set_custom_document_properties(
                document,
                {"LetterSubject": "new", "LetterNumber": "new-number"},
            )

        self.assertEqual(document.properties.values["LetterSubject"], "old")
        self.assertEqual(document.properties.values["LetterNumber"], "old-number")

    def test_reports_incomplete_rollback_without_exposing_property_values(self):
        class FailsDuringUpdateAndRollback(FakeUserProperties):
            def __init__(self):
                super().__init__()
                self.subject_calls = 0

            def setPropertyValue(self, name, value):
                if name == "LetterNumber":
                    raise RuntimeError("UNO failure")
                if name == "LetterSubject":
                    self.subject_calls += 1
                    if self.subject_calls > 1:
                        raise RuntimeError("rollback failure")
                super().setPropertyValue(name, value)

        document = FakeDocument()
        document.properties = FailsDuringUpdateAndRollback()
        document.properties.values["LetterNumber"] = "old-number"
        document.properties.info = FakePropertyInfo(document.properties.values)

        with self.assertRaisesRegex(
            WriterPropertyUpdateError,
            "custom_property_update_failed_and_rollback_incomplete",
        ) as caught:
            set_custom_document_properties(
                document,
                {"LetterSubject": "sensitive-new-value", "LetterNumber": "new-number"},
            )

        self.assertNotIn("sensitive-new-value", str(caught.exception))

    def test_batch_rejects_non_text_values(self):
        with self.assertRaisesRegex(TypeError, "custom_property_value_must_be_text"):
            set_custom_document_properties(FakeDocument(), {"LetterSubject": b"binary"})

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
