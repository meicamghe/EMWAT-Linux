import threading
import unittest

from emwat_linux.application_runtime import BridgeRuntime, BridgeRuntimeState


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
