#!/usr/bin/env python3
"""
Whisper GUI - A minimal PyQt6 application for voice recording with history buffer
"""

import sys
import os
import signal
import logging
import time
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QTableWidget, QLabel, QStatusBar,
        QSystemTrayIcon, QMenu, QSplitter
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QObject, QMetaObject, pyqtSlot, QUrl
    from PyQt6.QtGui import QColor, QFont, QIcon
    from PyQt6.QtWidgets import QHeaderView
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
except ImportError:
    print("❌ PyQt6 is not installed!")
    print("Install with: pip install PyQt6")
    sys.exit(1)


class CommandSignalEmitter(QObject):
    """Signal emitter for safely calling GUI methods from daemon threads"""
    toggle_signal = pyqtSignal()
    start_signal = pyqtSignal()
    stop_signal = pyqtSignal()

from ..command_bus import CommandBus
from ..config import WhisperRuntimeConfig
from ..controllers import RecordingEventCallbacks, WhisperRecordingController
from ..fifo_controller import FIFOCommandController
from ..dbus_controller import DBusCommandController
from ..hotkeys import HotkeyBackend
from ..ipc_controller import CommandController
from .actions import open_project_terminal, show_microphone_settings
from .config import GUIStorageManager, SingletonLockError
from .history_view import refresh_history_table as render_history_table
from .presenter import WhisperPresenter
from .project_sidebar import ProjectSidebar
from .projects import ProjectManager
from .ui import build_main_interface, configure_tray

logger = logging.getLogger(__name__)

class WhisperGUI(QMainWindow):
    """Main GUI window for Whisper voice recording application"""

    def __init__(self, command_controller: Optional[CommandController] = None):
        super().__init__()
        self.setWindowTitle("Whisper Voice Recording")
        self.setGeometry(100, 100, 900, 600)
        self._exiting = False
        self._initialized = False  # Track initialization completion

        # Initialize shared runtime config + controller
        try:
            self.runtime_config = WhisperRuntimeConfig(headless=True, debug=True)
            callbacks = RecordingEventCallbacks(on_error=self._on_controller_error)
            self.recording_controller = WhisperRecordingController(
                runtime_config=self.runtime_config,
                callbacks=callbacks,
            )
        except Exception as e:
            error_msg = f"❌ Failed to initialize Whisper: {e}"
            print(error_msg)
            sys.exit(1)

        # Initialize command controller (use FIFO by default if not provided)
        if command_controller is None:
            if DBusCommandController.__module__:
                logger.info("Attempting to start D-Bus command controller")
                try:
                    command_controller = DBusCommandController(debug=self.runtime_config.debug)
                except Exception as exc:
                    logger.warning("D-Bus controller unavailable (%s); falling back to FIFO", exc)
                    command_controller = FIFOCommandController(debug=self.runtime_config.debug)
            else:
                command_controller = FIFOCommandController(debug=self.runtime_config.debug)
        self.command_bus = CommandBus(command_controller)

        # History + presenter helpers
        self.storage = GUIStorageManager(self.runtime_config.paths)
        self.project_manager = ProjectManager(self.runtime_config.paths)
        self.presenter = WhisperPresenter(
            self.recording_controller,
            self.storage,
            self.project_manager
        )
        self.presenter.recording_started.connect(self._on_presenter_recording_started)
        self.presenter.recording_finished.connect(self._on_presenter_recording_finished)
        self.presenter.recording_error.connect(self._on_presenter_error)
        self.presenter.recording_status.connect(self.on_recording_status_update)
        self.presenter.transcription_ready.connect(self._on_presenter_transcription_ready)
        self.presenter.history_changed.connect(self.refresh_history_table)
        self.presenter.status_message.connect(self._on_presenter_status_message)
        self.presenter.codex_started.connect(self._on_codex_started)
        self.presenter.codex_finished.connect(self._on_codex_finished)
        self.presenter.codex_error.connect(self._on_codex_error)

        # Lock file lifecycle is managed by the singleton guard in main()

        # Create signal emitter for safe thread-to-Qt communication
        # (used by IPC controller to dispatch commands to main thread)
        self.command_emitter = CommandSignalEmitter()
        self.command_emitter.toggle_signal.connect(self._on_toggle_command)
        self.command_emitter.start_signal.connect(self.start_recording)
        self.command_emitter.stop_signal.connect(self.stop_recording)

        # Initialize audio player for completion sound
        self.audio_output = QAudioOutput()
        self.media_player = QMediaPlayer()
        self.media_player.setAudioOutput(self.audio_output)

        # Connect error signal for debugging
        self.media_player.errorOccurred.connect(
            lambda error, error_string: logger.error(f"Media player error: {error} - {error_string}")
        )

        # Load completion sound
        import os
        completion_sound = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'assets', 'sweet-transition-153787.mp3')
        completion_sound_abs = os.path.abspath(completion_sound)
        if os.path.exists(completion_sound):
            source_url = QUrl.fromLocalFile(completion_sound_abs)
            self.media_player.setSource(source_url)
            logger.info(f"Loaded completion sound: {completion_sound_abs}")
        else:
            logger.warning(f"Completion sound not found: {completion_sound_abs}")

        # Start the command bus (handles IPC communication)
        try:
            self.command_bus.subscribe("toggle", lambda _cmd: self.command_emitter.toggle_signal.emit())
            self.command_bus.subscribe("start", lambda _cmd: self.command_emitter.start_signal.emit())
            self.command_bus.subscribe("stop", lambda _cmd: self.command_emitter.stop_signal.emit())
            self.command_bus.start()
            logger.info("Command bus started; listening for external commands")
        except Exception as e:
            logger.exception("Error starting command bus: %s", e)

        # Start global hotkey listener (configurable chord)
        # IMPORTANT: Hotkey callback runs in a non-Qt thread (pynput listener thread)
        # We must use the command_emitter signal to safely communicate with Qt
        self.hotkey_backend = None
        if self.runtime_config.hotkeys.enabled:
            try:
                self.hotkey_backend = HotkeyBackend(
                    chord=self.runtime_config.hotkeys.chord,
                    callback=lambda: self.command_emitter.toggle_signal.emit(),
                )
                self.hotkey_backend.start()
                logger.info("Hotkey listener started (%s)", self.runtime_config.hotkeys.chord)
            except Exception as e:
                logger.exception("Hotkey listener not available: %s", e)

        # Recording control is now handled via Unix signals (SIGUSR1/SIGUSR2/SIGALRM)
        # External programs can control recording via: whisper-recording-toggle toggle/start/stop
        # KDE shortcuts invoke whisper-recording-toggle, which sends signals to this process
        # This approach is Wayland-compatible and has zero dependencies

        # Setup UI
        self.setup_ui()
        self.refresh_history_table()

        # Setup system tray
        self.setup_tray()

        # Mark initialization as complete
        self._initialized = True
        logger.info("WhisperGUI initialization complete")

    def setup_ui(self):
        """Create the user interface."""
        # Build the main interface first
        build_main_interface(self)

        # Create and integrate the project sidebar
        self.project_sidebar = ProjectSidebar(self.presenter, self)
        self.project_sidebar.project_selected.connect(self._on_project_selected)

        # Wrap central widget with sidebar in a splitter for resizable panels
        original_central = self.centralWidget()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(self.project_sidebar)
        splitter.addWidget(original_central)
        # Set initial sizes: sidebar 250px, main content takes rest
        splitter.setSizes([250, 800])
        # Allow collapsing the sidebar
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        self.setCentralWidget(splitter)

    def setup_tray(self):
        """Setup system tray icon and menu."""
        configure_tray(self)

    def toggle_window(self):
        """Toggle window visibility"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def tray_icon_activated(self, reason):
        """Handle tray icon activation (single click, double click, etc.)"""
        from PyQt6.QtWidgets import QSystemTrayIcon
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window()

    def _set_tray_icon_red(self):
        """Change tray icon to red (recording state)"""
        if self.tray_icon_red:
            self.tray_icon.setIcon(self.tray_icon_red)

    def _set_tray_icon_orange(self):
        """Change tray icon to orange (stopped/transcribing state)"""
        if self.tray_icon_orange:
            self.tray_icon.setIcon(self.tray_icon_orange)

    def _set_tray_icon_green(self):
        """Change tray icon to green (ready state)"""
        if self.tray_icon_green:
            self.tray_icon.setIcon(self.tray_icon_green)

    @pyqtSlot()
    def exit_app(self):
        """Exit the application completely"""
        if self._exiting:
            logger.debug("Exit already in progress, ignoring duplicate request")
            return
        self._exiting = True

        logger.info("Exit requested; shutting down presenter and background services")

        # Step 1: Shutdown presenter (stops recording workers)
        try:
            self.presenter.shutdown()
            logger.debug("Presenter shutdown complete")
        except Exception as e:
            logger.exception("Error during presenter shutdown: %s", e)

        # Step 2: Stop the hotkey listener
        # This must happen BEFORE stopping command_bus to avoid race conditions
        # where a hotkey press arrives while we're shutting down the IPC layer
        try:
            if self.hotkey_backend:
                logger.debug("Stopping hotkey backend...")
                self.hotkey_backend.stop()
                logger.info("Hotkey listener stopped")
        except Exception as e:
            logger.exception("Error stopping hotkey listener: %s", e)

        # Step 3: Stop the IPC command controller (FIFO/DBus)
        # This may block briefly if waiting for reader thread to wake up
        try:
            if hasattr(self, 'command_bus') and self.command_bus:
                logger.debug("Stopping command bus...")
                self.command_bus.stop()
                logger.info("Command bus stopped")
        except Exception as e:
            logger.exception("Error stopping command controller: %s", e)

        # Step 4: Hide tray icon and cleanup UI
        try:
            if hasattr(self, 'tray_icon'):
                self.tray_icon.hide()
                logger.debug("Tray icon hidden")
        except Exception as e:
            logger.exception("Error hiding tray icon: %s", e)

        # Step 5: Cleanup Whisper resources
        try:
            self.recording_controller.cleanup()
            logger.debug("Recording controller cleanup complete")
        except Exception as e:
            logger.exception("Error during recording controller cleanup: %s", e)

        # Step 6: Request Qt event loop to quit; main() handles final sys.exit
        try:
            app = QApplication.instance()
            if app:
                app.quit()
                logger.info("Qt application quit requested")
        except Exception as e:
            logger.exception("Error quitting Qt application: %s", e)

    def _on_toggle_command(self):
        """Handle toggle command - dynamically choose start or stop based on current state

        This method is called via Qt signal from either:
        1. Hotkey backend (pynput listener thread -> signal emission -> Qt main thread)
        2. IPC command bus (FIFO/DBus reader thread -> signal emission -> Qt main thread)

        Thread-safety is guaranteed by Qt's signal/slot mechanism.
        """
        if not self._initialized:
            logger.debug("Toggle command ignored; GUI not fully initialized yet")
            return

        if self._exiting:
            logger.debug("Toggle command ignored; application is exiting")
            return

        if self.presenter.is_recording:
            logger.info("Toggle command: stopping recording (current state: recording)")
            self.stop_recording()
        else:
            logger.info("Toggle command: starting recording (current state: idle)")
            self.start_recording()

    def on_terminal_button_clicked(self):
        """Open Xfce terminal in the Whisper project directory"""
        open_project_terminal(self)

    def on_settings_button_clicked(self):
        """Open microphone settings dialog"""
        show_microphone_settings(self)

    def start_recording(self):
        """Start recording"""
        logger.info("start_recording() invoked (is_recording=%s, _exiting=%s)",
                    self.presenter.is_recording, self._exiting)

        if self._exiting:
            logger.debug("Start recording ignored; application is exiting")
            return

        if not self.presenter.start_recording():
            self.status_label.setText("⚠️ Already recording...")
            logger.warning("Start ignored because presenter reports already recording")
        else:
            logger.debug("Recording started successfully")

    def stop_recording(self):
        """Stop recording"""
        logger.info("stop_recording() invoked (is_recording=%s, _exiting=%s)",
                    self.presenter.is_recording, self._exiting)

        if not self.presenter.is_recording:
            logger.debug("Stop ignored because presenter is not recording")
            return

        logger.debug("Requesting presenter to stop recording...")
        self.presenter.stop_recording()
        self.status_label.setText("⏳ Processing transcription...")
        self.stop_button.setEnabled(False)
        logger.debug("Stop recording request sent to presenter")


    def _on_presenter_recording_finished(self):
        """Handle recording completion"""
        # Restore start button and gray out stop button
        self.start_button.setStyleSheet(self.start_button_style_normal)
        self.start_button.setEnabled(True)
        self.stop_button.setStyleSheet(self.stop_button_style_inactive)
        # Update tray status and icon
        self.tray_status.setText("🎤 Ready")
        self._set_tray_icon_green()  # Change icon back to green when transcription is done
        # Play completion sound
        if self.media_player.source().isValid():
            logger.debug("Playing completion sound")
            self.media_player.play()
        else:
            logger.warning("Cannot play completion sound: media source is not valid")

    def _on_presenter_recording_started(self):
        """Update UI on recording start."""
        self.start_button.setStyleSheet(self.start_button_style_inactive)
        self.start_button.setEnabled(False)
        self.stop_button.setStyleSheet(self.stop_button_style_active)
        self.stop_button.setEnabled(True)
        self.status_label.setText("🎤 Recording... (Press Stop when done)")
        self.statusBar().showMessage("Recording in progress...")
        self.tray_status.setText("🎤 Recording...")
        self._set_tray_icon_red()

    def _on_presenter_transcription_ready(self, transcription: str):
        """Handle successful transcription"""
        text_preview = transcription.strip()[:50]
        self.status_label.setText(f"✅ Copied to clipboard: \"{text_preview}...\"")
        self.statusBar().showMessage("✅ Transcription copied to clipboard")

    def _on_presenter_status_message(self, message: str):
        """Display presenter-level status updates."""
        self.status_label.setText(message)
        self.statusBar().showMessage(message)

    def _on_codex_started(self):
        self.status_label.setText("⏳ Processing with Claude...")
        self.codex_button.setStyleSheet(self.codex_button_style_processing)
        self.codex_button.setEnabled(False)

    def _on_codex_finished(self):
        self.codex_button.setStyleSheet(self.codex_button_style_normal)
        self.codex_button.setEnabled(True)

    def _on_codex_error(self, error_msg: str):
        self.status_label.setText(f"❌ Error: {error_msg}")
        self.statusBar().showMessage(f"❌ Claude error: {error_msg}")

    def _on_presenter_error(self, error_msg: str):
        """Handle recording error"""
        self.status_label.setText(f"❌ Error: {error_msg}")
        self.statusBar().showMessage("Error during recording")

    def _on_controller_error(self, message: str):
        sys.stderr.write(f"Recording controller error: {message}\n")
        sys.stderr.flush()
        self.status_label.setText(f"❌ Recording error: {message}")

    def on_recording_status_update(self, status: str):
        """Handle status updates from recording worker"""
        self.status_label.setText(status)
        self.statusBar().showMessage(status)

        # Change icon to orange when recording pauses and transcription begins
        if "Stopping recording" in status or "processing audio" in status.lower():
            self._set_tray_icon_orange()

    def _on_project_selected(self, project_id: str) -> None:
        """Handle project selection from sidebar."""
        logger.debug(f"Project selected: {project_id}")
        self.refresh_history_table()

    def refresh_history_table(self):
        """Refresh the history table display"""
        render_history_table(self)


    def on_table_cell_clicked(self, row: int, column: int):
        """Handle table cell clicks to select rows"""
        current_selection = self.presenter.toggle_row_selection(row)
        if current_selection is None:
            self.statusBar().showMessage("Row deselected")
        else:
            history = self.presenter.history
            text_preview = history[row]["text"][:50] if row < len(history) else ""
            self.statusBar().showMessage(
                f"Row selected (click delete button to remove): {text_preview}..."
            )
        self.refresh_history_table()

    def on_codex_button_clicked(self):
        """Handle codex processing button click"""
        self.presenter.process_with_codex()

    def clear_history(self):
        """Clear history via presenter helper."""
        self.presenter.clear_history()

    def closeEvent(self, event):
        """Handle window close - minimize to tray instead of exiting"""
        # If recording is active, stop it properly using the GUI method (not direct Whisper call)
        if self.presenter.is_recording:
            self.stop_recording()

        # Wait for recording thread to finish before hiding window
        # This prevents X11/Wayland crashes during window hide
        self.presenter.wait_for_recording()

        # IMPORTANT: Do NOT delete lock file here - it should only be deleted on actual app exit
        # The lock file indicates the GUI is still running in the system tray
        # Only exit_app() and main's finally block should delete the lock file

        # Just hide the window, don't exit the app
        # The app continues running in the system tray
        self.hide()
        event.ignore()  # Ignore the close event to prevent app exit


def main():
    runtime_config = WhisperRuntimeConfig(headless=True, debug=True)
    logging.basicConfig(
        level=logging.DEBUG if runtime_config.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    storage = GUIStorageManager(runtime_config.paths)
    try:
        lock = storage.acquire_lock()
    except SingletonLockError:
        print("❌ Whisper GUI is already running!")
        print("Only one instance can run at a time.")
        sys.exit(1)

    lock.write_pid(os.getpid())

    app = QApplication(sys.argv)
    window = WhisperGUI()
    window.show()

    # Handle termination signals (Ctrl+C / systemd stop) to exit cleanly
    # Qt overrides signal handlers when app.exec() runs. Solution: use a simple
    # flag + watchdog that doesn't rely on Qt cooperation
    import threading

    shutdown_flag = [False]  # Use list for mutability in nested function

    def handle_shutdown_signal(signum, frame):
        """Signal handler that works despite Qt overriding handlers.

        Sets a flag and starts a watchdog that will force-exit if Qt doesn't cooperate.
        """
        if shutdown_flag[0]:
            # Second signal = immediate force kill
            os._exit(1)

        shutdown_flag[0] = True
        print("\n👋 Exiting...")

        # Watchdog thread: force exit after 3 seconds no matter what
        def force_exit():
            time.sleep(3.0)
            os._exit(1)

        threading.Thread(target=force_exit, daemon=True, name="ExitWatchdog").start()

        # Try to close Qt gracefully, but watchdog will kill us if it hangs
        try:
            QApplication.quit()
        except Exception:
            pass

    #  Register handlers. Note: Qt may override these when exec() runs!
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    try:
        # Qt overrides our signal handlers here, so we use a different approach:
        # Install a Unix signal wakeup file descriptor that Qt WILL respect
        import socket
        if hasattr(signal, 'set_wakeup_fd'):
            # Create a socket pair for signal wakeup
            signal_read_sock, signal_write_sock = socket.socketpair()
            signal_read_sock.setblocking(False)
            signal_write_sock.setblocking(False)

            # Tell Python to write to this socket when signal arrives
            old_wakeup_fd = signal.set_wakeup_fd(signal_write_sock.fileno())

            # Create a QSocketNotifier to watch for signals
            from PyQt6.QtCore import QSocketNotifier

            def handle_signal_wakeup(sock_fd):
                """Called when signal wakeup FD is written to."""
                # Read the signal number
                try:
                    data = signal_read_sock.recv(1)
                except (BlockingIOError, InterruptedError):
                    return

                logger.info("Signal wakeup detected; initiating shutdown")
                window.exit_app()

            notifier = QSocketNotifier(signal_read_sock.fileno(), QSocketNotifier.Type.Read)
            notifier.activated.connect(lambda: handle_signal_wakeup(signal_read_sock.fileno()))

        exit_code = app.exec()
        sys.exit(exit_code)
    finally:
        lock.release()


if __name__ == "__main__":
    main()
