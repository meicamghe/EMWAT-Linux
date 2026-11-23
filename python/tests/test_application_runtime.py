import threading
import unittest

from emwat_linux.application_runtime import BridgeRuntime, BridgeRuntimeState


class FakeServer:
    def __init__(self):
        self.entered = threading.Event()
        self.stopped = threading.Event()
        self.closed = False

    def serve_forever(self):
        self.entered.set()
        self.stopped.wait()

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

    def test_server_failure_is_retained_and_socket_closed(self):
        failure = RuntimeError("serve failed")

        class BrokenServer(FakeServer):
            def serve_forever(self):
                raise failure

        server = BrokenServer()
        runtime = BridgeRuntime(server)
        runtime.start()
        runtime.close()
        self.assertIs(runtime.failure, failure)
        self.assertEqual(runtime.state, BridgeRuntimeState.FAILED)
        self.assertTrue(server.closed)


if __name__ == "__main__":
    unittest.main()
