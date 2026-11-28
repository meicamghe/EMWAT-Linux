import contextlib
import io
import unittest


class GtkDesktopEntryTests(unittest.TestCase):
    def test_shutdown_stops_running_or_failed_bridge_but_not_idle(self):
        from types import SimpleNamespace
        from emwat_linux.gtk_desktop import _stop_bridge_supervisor_on_shutdown

        class Supervisor:
            def __init__(self, state):
                self.state = SimpleNamespace(value=state)
                self.stop_calls = 0

            def stop(self):
                self.stop_calls += 1
                self.state = SimpleNamespace(value="stopped")

        for state in ("running", "failed"):
            supervisor = Supervisor(state)
            _stop_bridge_supervisor_on_shutdown(supervisor)
            self.assertEqual(supervisor.stop_calls, 1)
            self.assertEqual(supervisor.state.value, "stopped")

        for state in ("idle", "stopped"):
            supervisor = Supervisor(state)
            _stop_bridge_supervisor_on_shutdown(supervisor)
            self.assertEqual(supervisor.stop_calls, 0)

        _stop_bridge_supervisor_on_shutdown(None)

    def test_import_does_not_load_gi_or_gtk(self):
        from emwat_linux import gtk_desktop

        self.assertEqual(gtk_desktop.APPLICATION_ID, "org.emwat.Linux")
        self.assertTrue(callable(gtk_desktop.create_desktop_application))

    def test_help_is_available_without_a_graphical_session(self):
        from emwat_linux.gtk_desktop import main

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("diagnostics and recovery", output.getvalue())

    def test_main_injects_default_recovery_controller(self):
        from unittest.mock import patch
        from emwat_linux import gtk_desktop

        application = type("Application", (), {"run": lambda self, _args: 7})()
        controller = object()
        supervisor = object()
        with (
            patch.object(gtk_desktop, "create_default_recovery_controller", return_value=controller),
            patch("emwat_linux.deployment.create_default_bridge_supervisor", return_value=supervisor),
            patch.object(gtk_desktop, "create_desktop_application", return_value=application) as create_app,
        ):
            self.assertEqual(gtk_desktop.main([]), 7)
        create_app.assert_called_once_with(
            recovery_controller=controller,
            bridge_supervisor=supervisor,
            auto_start_bridge=True,
        )

    def test_auto_start_requires_an_explicit_supervisor(self):
        from emwat_linux.gtk_desktop import create_desktop_application

        with self.assertRaisesRegex(ValueError, "auto_start_bridge_requires_bridge_supervisor"):
            create_desktop_application(auto_start_bridge=True)

    def test_desktop_module_does_not_compose_or_start_bridge(self):
        from emwat_linux import gtk_desktop

        source = __import__("inspect").getsource(gtk_desktop)
        self.assertNotIn("create_libreoffice_bridge_server", source)
        self.assertNotIn("BridgeRuntime(", source)


if __name__ == "__main__":
    unittest.main()
