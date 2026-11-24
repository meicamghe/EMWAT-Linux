import unittest


class GtkDesktopRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import gi
            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk
        except (ImportError, ValueError):
            raise unittest.SkipTest("GTK 4 / PyGObject is not installed")

        from emwat_linux.gtk_desktop import create_desktop_application

        cls.Gtk = Gtk
        cls.application = create_desktop_application()
        cls.application.register(None)
        cls.application.activate()
        cls.main_window = cls.application.get_active_window()
        if cls.main_window is None:
            raise AssertionError("GTK application did not create its main window")
        cls.extra_windows = []

    @classmethod
    def tearDownClass(cls):
        for window in cls.extra_windows:
            window.close()
        cls.main_window.close()
        cls.application.quit()

    def test_application_creates_control_window(self):
        self.assertIsInstance(self.main_window, self.Gtk.ApplicationWindow)
        self.assertEqual(self.main_window.get_title(), "EMWAT Linux")

    def test_recovery_picker_selects_newest_metadata_row(self):
        from types import SimpleNamespace
        from emwat_linux.gtk_recovery_view import build_recovery_picker

        entry = SimpleNamespace(
            session_id="session-newest",
            document_name="letter.doc",
            size_bytes=128,
            updated_at=1_800_000_000.0,
        )
        state = SimpleNamespace(
            entries=(entry,),
            selected_session_id=entry.session_id,
            selected_entry=entry,
            is_empty=False,
        )
        controller = SimpleNamespace(state=lambda _selected=None: state)
        window = build_recovery_picker(self.application, controller)
        self.extra_windows.append(window)

        root = window.get_child()
        status = root.get_first_child().get_next_sibling().get_next_sibling()
        scroller = status.get_next_sibling()
        listing = scroller.get_child()
        # Gtk.ScrolledWindow may insert a Gtk.Viewport around a non-scrollable
        # child. Unwrap it rather than assuming get_child() is always ListBox.
        if isinstance(listing, self.Gtk.Viewport):
            listing = listing.get_child()
        self.assertIsInstance(listing, self.Gtk.ListBox)
        selected = listing.get_selected_row()
        self.assertIsNotNone(selected)
        self.assertEqual(selected.get_name(), "session-newest")
        actions = root.get_last_child()
        restore_button = actions.get_first_child().get_next_sibling()
        discard_button = restore_button.get_next_sibling()
        self.assertTrue(restore_button.get_sensitive())
        self.assertTrue(discard_button.get_sensitive())

    def test_z_main_window_can_reopen_while_recovery_window_is_open(self):
        self.assertTrue(self.extra_windows)
        self.main_window.close()
        self.application.activate()
        reopened = self.application.get_active_window()
        self.assertIsNotNone(reopened)
        self.assertEqual(reopened.get_title(), "EMWAT Linux")
        self.extra_windows.append(reopened)

    def test_recovery_picker_builds_with_empty_catalog(self):
        from types import SimpleNamespace
        from emwat_linux.gtk_recovery_view import build_recovery_picker

        state = SimpleNamespace(
            entries=(),
            selected_session_id=None,
            selected_entry=None,
            is_empty=True,
        )
        controller = SimpleNamespace(state=lambda _selected=None: state)
        window = build_recovery_picker(self.application, controller)
        self.extra_windows.append(window)
        self.assertEqual(window.get_title(), "EMWAT — Recovery")
        actions = window.get_child().get_last_child()
        restore_button = actions.get_first_child().get_next_sibling()
        discard_button = restore_button.get_next_sibling()
        self.assertFalse(restore_button.get_sensitive())
        self.assertFalse(discard_button.get_sensitive())
        window.present()


    @staticmethod
    def _walk_widgets(widget):
        yield widget
        child = widget.get_first_child()
        while child is not None:
            yield from GtkDesktopRuntimeTests._walk_widgets(child)
            child = child.get_next_sibling()

    def test_bridge_controls_are_visible_but_disabled_without_supervisor(self):
        widgets = tuple(self._walk_widgets(self.main_window.get_child()))
        buttons = {
            widget.get_label(): widget
            for widget in widgets
            if isinstance(widget, self.Gtk.Button)
        }
        self.assertIn("شروع سرویس", buttons)
        self.assertIn("توقف سرویس", buttons)
        self.assertFalse(buttons["شروع سرویس"].get_sensitive())
        self.assertFalse(buttons["توقف سرویس"].get_sensitive())
        labels = [
            widget.get_text()
            for widget in widgets
            if isinstance(widget, self.Gtk.Label)
        ]
        self.assertTrue(
            any("پیکربندی نشده" in label for label in labels),
            labels,
        )

    def test_injected_bridge_supervisor_controls_run_off_gtk_thread(self):
        import threading
        import time
        from types import SimpleNamespace
        import emwat_linux.gtk_desktop as gtk_desktop

        class FakeSupervisor:
            def __init__(self):
                self._state = "idle"
                self._failure = None
                self.started = threading.Event()
                self.stopped = threading.Event()
                self.operation_threads = []

            @property
            def state(self):
                return SimpleNamespace(value=self._state)

            @property
            def failure(self):
                return self._failure

            def start(self):
                self.operation_threads.append(threading.current_thread())
                self._state = "running"
                self.started.set()

            def stop(self):
                self.operation_threads.append(threading.current_thread())
                self._state = "stopped"
                self.stopped.set()

        supervisor = FakeSupervisor()
        # The test fixture already owns the normal application ID. Give this
        # independent application a distinct D-Bus object path while keeping
        # the production application ID unchanged.
        original_application_id = gtk_desktop.APPLICATION_ID
        gtk_desktop.APPLICATION_ID = "org.emwat.Linux.BridgeControlTest"
        try:
            application = gtk_desktop.create_desktop_application(
                bridge_supervisor=supervisor
            )
        finally:
            gtk_desktop.APPLICATION_ID = original_application_id
        application.register(None)
        application.activate()
        window = application.get_active_window()
        self.extra_windows.append(window)
        self.addCleanup(application.quit)
        self.assertFalse(supervisor.started.is_set(), "window activation must not auto-start the Bridge")
        self.assertEqual(supervisor.state.value, "idle")

        widgets = tuple(self._walk_widgets(window.get_child()))
        buttons = {
            widget.get_label(): widget
            for widget in widgets
            if isinstance(widget, self.Gtk.Button)
        }
        self.assertTrue(buttons["شروع سرویس"].get_sensitive())
        self.assertFalse(buttons["توقف سرویس"].get_sensitive())

        buttons["شروع سرویس"].emit("clicked")
        deadline = time.monotonic() + 3.0
        from gi.repository import GLib
        main_context = GLib.MainContext.default()
        while time.monotonic() < deadline:
            while main_context.pending():
                main_context.iteration(False)
            if supervisor.started.is_set() and "running" in [
                item.get_text()
                for item in self._walk_widgets(window.get_child())
                if isinstance(item, self.Gtk.Label)
            ]:
                break
            time.sleep(0.005)
        self.assertTrue(supervisor.started.is_set(), "start operation did not run")
        self.assertTrue(supervisor.operation_threads)
        self.assertNotEqual(
            supervisor.operation_threads[0],
            threading.current_thread(),
            "supervisor operation blocked the GTK thread",
        )
        self.assertTrue(buttons["توقف سرویس"].get_sensitive())

        # Simulate an unexpected serving-thread exit without a button action.
        # The periodic GTK-main-context poll must surface it and retain Stop.
        supervisor._state = "failed"
        supervisor._failure = RuntimeError("simulated serve-loop exit")
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            while main_context.pending():
                main_context.iteration(False)
            labels = [
                item.get_text()
                for item in self._walk_widgets(window.get_child())
                if isinstance(item, self.Gtk.Label)
            ]
            if any("simulated serve-loop exit" in label for label in labels):
                break
            time.sleep(0.01)
        self.assertTrue(
            any("simulated serve-loop exit" in label for label in labels),
            labels,
        )
        self.assertTrue(buttons["توقف سرویس"].get_sensitive())

        buttons["توقف سرویس"].emit("clicked")
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            while main_context.pending():
                main_context.iteration(False)
            if supervisor.stopped.is_set() and "stopped" in [
                item.get_text()
                for item in self._walk_widgets(window.get_child())
                if isinstance(item, self.Gtk.Label)
            ]:
                break
            time.sleep(0.005)
        self.assertTrue(supervisor.stopped.is_set(), "stop operation did not run")
        self.assertTrue(buttons["شروع سرویس"].get_sensitive())
        window.close()


    def test_application_shutdown_waits_for_inflight_start_then_stops_bridge(self):
        import threading
        import time
        from types import SimpleNamespace
        import emwat_linux.gtk_desktop as gtk_desktop

        class FakeSupervisor:
            def __init__(self):
                self._state = "idle"
                self._failure = None
                self.started = threading.Event()
                self.release_start = threading.Event()
                self.stopped = threading.Event()
                self.operations = []

            @property
            def state(self):
                return SimpleNamespace(value=self._state)

            @property
            def failure(self):
                return self._failure

            def start(self):
                self.operations.append("start")
                self._state = "starting"
                self.started.set()
                if not self.release_start.wait(3.0):
                    raise TimeoutError("test_start_release_timed_out")
                self._state = "running"

            def stop(self):
                self.operations.append("stop")
                if self._state in ("running", "failed"):
                    self._state = "stopped"
                    self.stopped.set()

        supervisor = FakeSupervisor()
        original_application_id = gtk_desktop.APPLICATION_ID
        gtk_desktop.APPLICATION_ID = "org.emwat.Linux.ShutdownRaceTest"
        try:
            application = gtk_desktop.create_desktop_application(
                bridge_supervisor=supervisor
            )
        finally:
            gtk_desktop.APPLICATION_ID = original_application_id

        application.register(None)
        application.activate()
        window = application.get_active_window()
        self.extra_windows.append(window)
        self.addCleanup(application.quit)

        widgets = tuple(self._walk_widgets(window.get_child()))
        start_button = next(
            widget for widget in widgets
            if isinstance(widget, self.Gtk.Button)
            and widget.get_label() == "شروع سرویس"
        )
        start_button.emit("clicked")
        self.assertTrue(
            supervisor.started.wait(3.0),
            "bridge start worker did not enter the operation",
        )

        shutdown_finished = threading.Event()

        def emit_shutdown():
            application.emit("shutdown")
            shutdown_finished.set()

        shutdown_thread = threading.Thread(
            target=emit_shutdown,
            name="emwat-test-gtk-shutdown",
            daemon=True,
        )
        shutdown_thread.start()
        time.sleep(0.05)
        self.assertFalse(
            shutdown_finished.is_set(),
            "shutdown must wait for the in-flight start operation",
        )

        supervisor.release_start.set()
        shutdown_thread.join(timeout=3.0)
        self.assertFalse(shutdown_thread.is_alive(), "shutdown callback did not finish")
        self.assertTrue(shutdown_finished.is_set())
        self.assertTrue(supervisor.stopped.is_set())
        self.assertEqual(supervisor.operations, ["start", "stop"])
        self.assertEqual(supervisor.state.value, "stopped")


if __name__ == "__main__":
    unittest.main()
