import threading
import unittest

from emwat_linux.application_runtime import BridgeRuntime, BridgeRuntimeState
from emwat_linux.bridge import BridgeHTTPServer, BridgeResponse


class FakeServer:
    def __init__(self):
        self.entered = threading.Event()
        self.serving = threading.Event()
        self.stopped = threading.Event()
        self.closed = False

    def serve_forever(self):
        try:
            self.entered.set()
            self.serving.set()
            self.stopped.wait()
        finally:
            self.serving.set()

    def wait_until_serving(self):
        self.serving.wait()

    def shutdown(self):
        self.stopped.set()

    def server_close(self):
        self.closed = True


class BridgeRuntimeTests(unittest.TestCase):
    def test_start_and_close_supervise_server_thread(self):
        server = FakeServer()
        runtime = BridgeRuntime(server)
        runtime.start()
        self.assertTrue(server.entered.wait(2))
        self.assertEqual(runtime.state, BridgeRuntimeState.RUNNING)
        runtime.close()
        self.assertTrue(server.closed)
        self.assertEqual(runtime.state, BridgeRuntimeState.STOPPED)

    def test_immediate_close_after_real_bridge_start_is_safe(self):
        server = BridgeHTTPServer(
            lambda _request: BridgeResponse(b""),
            require_origin=False,
        )
        runtime = BridgeRuntime(server)
        runtime.start()
        runtime.close()
        self.assertEqual(runtime.state, BridgeRuntimeState.STOPPED)

    def test_runtime_is_one_shot(self):
        runtime = BridgeRuntime(FakeServer())
        runtime.start()
        with self.assertRaisesRegex(RuntimeError, "cannot_start"):
            runtime.start()
        runtime.close()
        with self.assertRaisesRegex(RuntimeError, "cannot_start"):
            runtime.start()

    def test_close_before_start_releases_bound_server(self):
        server = FakeServer()
        runtime = BridgeRuntime(server)
        runtime.close()
        self.assertTrue(server.closed)
        self.assertEqual(runtime.state, BridgeRuntimeState.STOPPED)
        self.assertFalse(server.entered.is_set())

    def test_context_manager_closes_server(self):
        server = FakeServer()
        with BridgeRuntime(server) as runtime:
            self.assertTrue(server.entered.wait(2))
            self.assertEqual(runtime.state, BridgeRuntimeState.RUNNING)
        self.assertTrue(server.closed)
        self.assertEqual(runtime.state, BridgeRuntimeState.STOPPED)


    def test_close_cannot_race_a_server_that_has_not_entered_serve_loop(self):
        allow_serve = threading.Event()
        shutdown_called = threading.Event()

        class SlowStartingServer(FakeServer):
            def serve_forever(self):
                self.entered.set()
                allow_serve.wait(2)
                self.serving.set()
                self.stopped.wait()

            def shutdown(self):
                shutdown_called.set()
                self.stopped.set()

        server = SlowStartingServer()
        runtime = BridgeRuntime(server)
        start_done = threading.Event()
        close_done = threading.Event()
        starter = threading.Thread(target=lambda: (runtime.start(), start_done.set()))
        starter.start()
        self.assertTrue(server.entered.wait(2))

        closer = threading.Thread(target=lambda: (runtime.close(), close_done.set()))
        closer.start()
        self.assertFalse(shutdown_called.wait(0.05))
        self.assertFalse(close_done.is_set())

        allow_serve.set()
        starter.join(2)
        closer.join(2)
        self.assertTrue(start_done.is_set())
        self.assertTrue(close_done.is_set())
        self.assertTrue(shutdown_called.is_set())
        self.assertEqual(runtime.state, BridgeRuntimeState.STOPPED)

    def test_concurrent_close_callers_all_wait_for_socket_close(self):
        entered_shutdown = threading.Event()
        release_shutdown = threading.Event()

        class SlowCloseServer(FakeServer):
            def shutdown(self):
                entered_shutdown.set()
                release_shutdown.wait(2)
                self.stopped.set()

        server = SlowCloseServer()
        runtime = BridgeRuntime(server)
        runtime.start()
        self.assertTrue(server.entered.wait(2))
        first_done = threading.Event()
        second_done = threading.Event()
        first = threading.Thread(target=lambda: (runtime.close(), first_done.set()))
        second = threading.Thread(target=lambda: (runtime.close(), second_done.set()))
        first.start()
        self.assertTrue(entered_shutdown.wait(2))
        second.start()
        self.assertFalse(second_done.wait(0.05))
        release_shutdown.set()
        first.join(2)
        second.join(2)
        self.assertTrue(first_done.is_set())
        self.assertTrue(second_done.is_set())
        self.assertTrue(server.closed)
        self.assertEqual(runtime.state, BridgeRuntimeState.STOPPED)

    def test_shutdown_failure_still_closes_socket_and_joins_thread(self):
        failure = RuntimeError("shutdown failed")

        class FailingShutdownServer(FakeServer):
            def shutdown(self):
                self.stopped.set()
                raise failure

        server = FailingShutdownServer()
        runtime = BridgeRuntime(server)
        runtime.start()
        with self.assertRaisesRegex(RuntimeError, "shutdown failed"):
            runtime.close()
        self.assertTrue(server.closed)
        self.assertFalse(runtime._thread.is_alive())
        self.assertIs(runtime.failure, failure)
        self.assertEqual(runtime.state, BridgeRuntimeState.FAILED)

    def test_shutdown_failure_has_bounded_join_and_can_be_retried(self):
        failure = RuntimeError("shutdown failed before stop signal")

        class RetryShutdownServer(FakeServer):
            def __init__(self):
                super().__init__()
                self.shutdown_attempts = 0

            def shutdown(self):
                self.shutdown_attempts += 1
                if self.shutdown_attempts == 1:
                    raise failure
                self.stopped.set()

        server = RetryShutdownServer()
        runtime = BridgeRuntime(server, join_timeout_seconds=0.01)
        runtime.start()
        with self.assertRaisesRegex(RuntimeError, "before stop signal"):
            runtime.close()

        self.assertTrue(server.closed)
        self.assertTrue(runtime._thread.is_alive())
        self.assertEqual(runtime.state, BridgeRuntimeState.FAILED)
        self.assertIs(runtime.failure, failure)

        # A later close retries shutdown while the serve thread is still alive.
        runtime.close()
        self.assertEqual(server.shutdown_attempts, 2)
        self.assertFalse(runtime._thread.is_alive())
        self.assertEqual(runtime.state, BridgeRuntimeState.STOPPED)
        self.assertIsNone(runtime.failure)

    def test_join_timeout_must_be_finite_and_non_negative(self):
        for invalid in (-1, float("inf"), float("nan"), True, 10**1000):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "join_timeout_seconds"):
                    BridgeRuntime(FakeServer(), join_timeout_seconds=invalid)

    def test_close_before_start_retries_socket_close_after_failure(self):
        failure = RuntimeError("server_close failed")

        class RetryCloseServer(FakeServer):
            def __init__(self):
                super().__init__()
                self.close_attempts = 0

            def server_close(self):
                self.close_attempts += 1
                if self.close_attempts == 1:
                    raise failure
                self.closed = True

        server = RetryCloseServer()
        runtime = BridgeRuntime(server)
        with self.assertRaisesRegex(RuntimeError, "server_close failed"):
            runtime.close()
        self.assertEqual(runtime.state, BridgeRuntimeState.FAILED)
        self.assertFalse(server.closed)
        runtime.close()
        self.assertTrue(server.closed)
        self.assertEqual(server.close_attempts, 2)
        self.assertEqual(runtime.state, BridgeRuntimeState.STOPPED)
        self.assertIsNone(runtime.failure)

    def test_server_failure_is_retained_and_socket_closed(self):
        failure = RuntimeError("serve failed")

        class BrokenServer(FakeServer):
            def serve_forever(self):
                try:
                    raise failure
                finally:
                    self.serving.set()

        server = BrokenServer()
        runtime = BridgeRuntime(server)
        runtime.start()
        runtime.close()
        self.assertIs(runtime.failure, failure)
        self.assertEqual(runtime.state, BridgeRuntimeState.FAILED)
        self.assertTrue(server.closed)


if __name__ == "__main__":
    unittest.main()
