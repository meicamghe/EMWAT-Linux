import unittest

from emwat_linux.close_trace import CloseLifecycleTrace


class CloseLifecycleTraceTests(unittest.TestCase):
    def test_records_fixed_event_names_and_attempt_ordinals(self):
        trace = CloseLifecycleTrace()
        trace.record("query_closing")
        trace.record("snapshot_succeeded")
        trace.record("query_closing")
        trace.record("snapshot_failed")
        trace.record("notify_closed")

        events = trace.snapshot()
        self.assertEqual(
            [event.name for event in events],
            [
                "query_closing",
                "snapshot_succeeded",
                "query_closing",
                "snapshot_failed",
                "notify_closed",
            ],
        )
        self.assertEqual(
            [event.attempt for event in events],
            [1, 1, 2, 2, 2],
        )
        self.assertEqual([event.sequence for event in events], [1, 2, 3, 4, 5])
        self.assertTrue(
            all(left.monotonic_ns <= right.monotonic_ns for left, right in zip(events, events[1:]))
        )
        self.assertEqual(trace.attempt_count, 2)

    def test_rejects_unrecognized_event_names(self):
        trace = CloseLifecycleTrace()
        with self.assertRaisesRegex(ValueError, "unsupported_close_trace_event"):
            trace.record("document_text:" + "secret")
        self.assertEqual(trace.snapshot(), ())


if __name__ == "__main__":
    unittest.main()
