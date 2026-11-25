import unittest

from emwat_linux.sessions import (
    DocumentSession,
    DocumentState,
    InvalidTransition,
)


class DocumentSessionTests(unittest.TestCase):
    def opened_session(self):
        session = DocumentSession("doc-1")
        session.begin_initialization()
        session.mark_opened()
        return session

    def test_initialization_and_open_transitions(self):
        session = DocumentSession("doc-1")
        self.assertEqual(session.state, DocumentState.CREATED)
        session.begin_initialization()
        self.assertEqual(session.state, DocumentState.INITIALIZING)
        session.mark_opened()
        self.assertEqual(session.state, DocumentState.OPENED)

    def test_edit_increments_revision(self):
        session = self.opened_session()
        self.assertEqual(session.mark_dirty(), 1)
        self.assertEqual(session.mark_dirty(), 2)
        self.assertEqual(session.state, DocumentState.DIRTY)

    def test_engine_save_does_not_return_document(self):
        session = self.opened_session()
        session.mark_dirty()
        session.record_engine_save()
        self.assertEqual(session.saved_revision, 1)
        self.assertEqual(session.state, DocumentState.DIRTY)
        self.assertIsNone(session.returned_payload)

    def test_dirty_session_can_finalize_using_adapter_selected_approved_snapshot(self):
        session = self.opened_session()
        session.mark_dirty()
        self.assertIsNone(session.saved_revision)
        self.assertTrue(session.begin_finalize())
        self.assertTrue(session.complete_finalize(b"final-document"))
        self.assertEqual(session.state, DocumentState.RETURNED)
        self.assertEqual(session.returned_payload, b"final-document")

    def test_finalize_is_idempotent_for_same_payload(self):
        session = self.opened_session()
        self.assertTrue(session.begin_finalize())
        self.assertFalse(session.begin_finalize())
        self.assertTrue(session.complete_finalize(b"doc"))
        self.assertFalse(session.begin_finalize())
        self.assertFalse(session.complete_finalize(b"doc"))

    def test_conflicting_second_return_is_rejected(self):
        session = self.opened_session()
        session.begin_finalize()
        session.complete_finalize(b"first")
        with self.assertRaises(InvalidTransition):
            session.complete_finalize(b"second")

    def test_invalid_transition_is_rejected(self):
        session = DocumentSession("doc-1")
        with self.assertRaises(InvalidTransition):
            session.mark_opened()
        with self.assertRaises(InvalidTransition):
            session.begin_finalize()

    def test_failure_is_terminal_but_cancelled_close_attempt_keeps_session_open(self):
        failed = self.opened_session()
        failed.fail("writer_crashed")
        self.assertEqual(failed.state, DocumentState.FAILED)
        self.assertEqual(failed.failure_reason, "writer_crashed")
        with self.assertRaises(InvalidTransition):
            failed.begin_finalize()

        cancelled = self.opened_session()
        cancelled.mark_dirty()
        cancelled.cancel_close_attempt()
        self.assertEqual(cancelled.state, DocumentState.DIRTY)
        self.assertEqual(cancelled.revision, 1)
        self.assertTrue(cancelled.begin_finalize())

        terminal = self.opened_session()
        terminal.cancel()
        self.assertEqual(terminal.state, DocumentState.CANCELLED)
        with self.assertRaises(InvalidTransition):
            terminal.begin_finalize()

    def test_session_id_validation(self):
        for value in ("", " doc-1", "doc-1 "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                DocumentSession(value)


if __name__ == "__main__":
    unittest.main()
