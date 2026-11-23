import threading
import unittest

from emwat_linux.application_runtime import BridgeRuntime, BridgeRuntimeState
from emwat_linux.bridge_supervisor import (
    BridgeSupervisor,
    BridgeSupervisorState,
)


class FakeServer:
    def __init__(self):
        self.entered = threading.Event()
        self.serving = threading.Event()
        self.stopped = threading.Event()
        self.closed = False
        self.shutdown_calls = 0

    def serve_forever(self):
        self.entered.set()
        self.serving.set()
        self.stopped.wait()

    def wait_until_serving(self):
        self.serving.wait(2)

    def shutdown(self):
        self.shutdown_calls += 1
        self.stopped.set()

    def server_close(self):
        self.closed = True


class BridgeSupervisorTests(unittest.TestCase):
    def test_start_is_idempotent_and_stop_closes_runtime(self):
        servers = []

        def factory():
            server = FakeServer()
            servers.append(server)
            return server

        supervisor = BridgeSupervisor(factory)
        runtime = supervisor.start()
        self.assertIs(supervisor.start(), runtime)
        self.assertEqual(len(servers), 1)
        self.assertEqual(supervisor.state, BridgeSupervisorState.RUNNING)
        self.assertEqual(runtime.state, BridgeRuntimeState.RUNNING)

        supervisor.stop()
        self.assertTrue(servers[0].closed)
        self.assertEqual(supervisor.state, BridgeSupervisorState.STOPPED)
        self.assertIsNone(supervisor.failure)

    def test_start_after_successful_stop_uses_fresh_one_shot_server(self):
        servers = []

        def factory():
            server = FakeServer()
            servers.append(server)
            return server

        supervisor = BridgeSupervisor(factory)
        first = supervisor.start()
        supervisor.stop()
        second = supervisor.start()

        self.assertIsNot(first, second)
        self.assertEqual(len(servers), 2)
        self.assertTrue(servers[0].closed)
        self.assertEqual(supervisor.state, BridgeSupervisorState.RUNNING)
        supervisor.stop()
        self.assertTrue(servers[1].closed)

    def test_failed_cleanup_blocks_restart_until_stop_retry_succeeds(self):
        class RetryServer(FakeServer):
            def __init__(self):
                super().__init__()
                self.fail_first_shutdown = True

            def shutdown(self):
                self.shutdown_calls += 1
                if self.fail_first_shutdown:
                    self.fail_first_shutdown = False
                    raise RuntimeError("transient shutdown failure")
                self.stopped.set()

        server = RetryServer()
        supervisor = BridgeSupervisor(
            lambda: server,
            runtime_factory=lambda item: BridgeRuntime(item, join_timeout_seconds=0.01),
        )
        supervisor.start()

        with self.assertRaisesRegex(RuntimeError, "transient shutdown failure"):
            supervisor.stop()
        self.assertEqual(supervisor.state, BridgeSupervisorState.FAILED)
        self.assertIsNotNone(supervisor.failure)

        with self.assertRaisesRegex(RuntimeError, "requires_successful_cleanup"):
            supervisor.start()

        supervisor.stop()
        self.assertEqual(supervisor.state, BridgeSupervisorState.STOPPED)
        self.assertIsNone(supervisor.failure)
        supervisor.start()
        supervisor.stop()

    def test_factory_failure_is_reported_and_can_be_retried(self):
        attempts = 0

        def factory():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("configuration unavailable")
            return FakeServer()

        supervisor = BridgeSupervisor(factory)
        with self.assertRaisesRegex(RuntimeError, "configuration unavailable"):
            supervisor.start()
        self.assertEqual(supervisor.state, BridgeSupervisorState.FAILED)
        self.assertIsNotNone(supervisor.failure)

        # No runtime was created, so stop transitions to a clean stopped state.
        supervisor.stop()
        runtime = supervisor.start()
        self.assertEqual(supervisor.state, BridgeSupervisorState.RUNNING)
        self.assertIsNotNone(runtime)
        supervisor.stop()

    def test_stop_before_start_is_safe_and_idempotent(self):
        supervisor = BridgeSupervisor(FakeServer)
        supervisor.stop()
        supervisor.stop()
        self.assertEqual(supervisor.state, BridgeSupervisorState.STOPPED)
        self.assertIsNone(supervisor.runtime)


    def test_runtime_factory_failure_closes_created_server(self):
        server = FakeServer()

        def broken_runtime_factory(_server):
            raise ValueError("invalid server configuration")

        supervisor = BridgeSupervisor(
            lambda: server,
            runtime_factory=broken_runtime_factory,
        )
        with self.assertRaisesRegex(ValueError, "invalid server configuration"):
            supervisor.start()
        self.assertTrue(server.closed)
        self.assertEqual(supervisor.state, BridgeSupervisorState.FAILED)
        supervisor.stop()
        self.assertEqual(supervisor.state, BridgeSupervisorState.STOPPED)

    def test_unexpected_runtime_exit_is_reported_and_cleanup_allows_restart(self):
        server = FakeServer()
        servers = [server]

        def factory():
            if servers:
                return servers.pop(0)
            return FakeServer()

        supervisor = BridgeSupervisor(factory)
        runtime = supervisor.start()
        server.stopped.set()
        runtime._thread.join(2)

        # Observe the asynchronous exit without issuing a second start.
        self.assertEqual(supervisor.state, BridgeSupervisorState.FAILED)
        self.assertIsNotNone(supervisor.failure)
        with self.assertRaisesRegex(RuntimeError, "requires_successful_cleanup"):
            supervisor.start()

        supervisor.stop()
        self.assertEqual(supervisor.state, BridgeSupervisorState.STOPPED)
        self.assertIsNotNone(supervisor.failure)
        replacement = supervisor.start()
        self.assertIsNot(replacement, runtime)
        supervisor.stop()

    def test_invalid_factories_are_rejected(self):
        with self.assertRaisesRegex(TypeError, "server_factory"):
            BridgeSupervisor(None)
        with self.assertRaisesRegex(TypeError, "runtime_factory"):
            BridgeSupervisor(FakeServer, runtime_factory=None)


if __name__ == "__main__":
    unittest.main()
