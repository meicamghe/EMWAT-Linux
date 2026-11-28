import http.client
import socket
import threading
import time
import unittest

from emwat_linux.application_runtime import BridgeRuntime, BridgeRuntimeState
from emwat_linux.bridge import BridgeHTTPServer, BridgeResponse
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
    def test_runtime_bounds_active_http_request_drain_and_allows_cleanup_retry(self):
        request_entered = threading.Event()
        release_request = threading.Event()
        response_result = {}

        def handler(_request):
            request_entered.set()
            if not release_request.wait(3):
                raise TimeoutError("test_request_release_timeout")
            return BridgeResponse(b"completed", content_type="text/plain")

        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        server = BridgeHTTPServer(
            handler,
            host="127.0.0.1",
            port=port,
            allowed_origins=frozenset({"http://127.0.0.1"}),
        )
        runtime = BridgeRuntime(
            server,
            join_timeout_seconds=1.0,
            request_drain_timeout_seconds=0.05,
        )

        def send_request():
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            try:
                connection.request(
                    "POST",
                    "/?invoke=12345",
                    body=b"pending",
                    headers={
                        "Origin": "http://127.0.0.1",
                        "Content-Type": "text/plain",
                    },
                )
                response = connection.getresponse()
                response_result["status"] = response.status
                response_result["body"] = response.read()
            except BaseException as exc:
                response_result["error"] = exc
            finally:
                connection.close()

        request_thread = threading.Thread(
            target=send_request,
            name="emwat-test-pending-http-request",
            daemon=True,
        )
        runtime.start()
        request_thread.start()
        try:
            self.assertTrue(request_entered.wait(2), "HTTP handler did not start")
            started = time.monotonic()
            with self.assertRaisesRegex(
                TimeoutError, "bridge_request_workers_did_not_drain"
            ):
                runtime.close()
            self.assertLess(time.monotonic() - started, 1.0)
            self.assertEqual(runtime.state, BridgeRuntimeState.FAILED)

            # The listener is stopped, but the active non-daemon request is
            # deliberately allowed to finish; a second close then owns cleanup.
            release_request.set()
            request_thread.join(timeout=2)
            self.assertFalse(request_thread.is_alive())
            self.assertNotIn("error", response_result)
            self.assertEqual(response_result, {"status": 200, "body": b"completed"})

            runtime.close()
            self.assertEqual(runtime.state, BridgeRuntimeState.STOPPED)
        finally:
            release_request.set()
            if request_thread.is_alive():
                request_thread.join(timeout=2)
            if runtime.state not in (BridgeRuntimeState.STOPPED,):
                try:
                    runtime.close()
                except BaseException:
                    pass


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
