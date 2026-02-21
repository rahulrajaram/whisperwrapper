#!/usr/bin/env python3
"""
Whisper GUI - A minimal PyQt6 application for voice recording with history buffer
"""

import sys
import json
import os
import signal
import threading
import subprocess
import socket
from pathlib import Path
from datetime import datetime
from typing import List

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QTableWidget, QTableWidgetItem, QLabel, QStatusBar,
        QSystemTrayIcon, QMenu
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
    from PyQt6.QtGui import QColor, QFont, QIcon
    from PyQt6.QtWidgets import QHeaderView
except ImportError:
    print("❌ PyQt6 is not installed!")
    print("Install with: pip install PyQt6")
    sys.exit(1)


class CommandSignalEmitter(QObject):
    """Signal emitter for safely calling GUI methods from daemon threads"""
    toggle_signal = pyqtSignal()
    start_signal = pyqtSignal()
    stop_signal = pyqtSignal()

from .cli import WhisperCLI
from .ipc_controller import CommandController
from .fifo_controller import FIFOCommandController
import re
from typing import Optional

def markdown_to_html(text: str) -> str:
    """Convert markdown **bold** to HTML <b>bold</b> for GUI display"""
    # Replace **text** with <b>text</b>
    html_text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    return html_text


class ClickableLabel(QLabel):
    """Custom QLabel that emits a signal when clicked"""
    clicked = pyqtSignal(int)  # Emits row index

    def __init__(self, text, row_index, parent=None):
        super().__init__(text, parent)
        self.row_index = row_index

    def mousePressEvent(self, event):
        """Emit clicked signal with row index when label is clicked"""
        self.clicked.emit(self.row_index)
        super().mousePressEvent(event)


class RecordingWorker(QObject):
    """Worker thread for non-blocking recording operations"""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(str)  # Emits the transcribed text
    stopped = pyqtSignal()
    status_update = pyqtSignal(str)  # For progress feedback

    def __init__(self, whisper_cli: WhisperCLI):
        super().__init__()
        self.whisper_cli = whisper_cli
        self.should_stop = False

    def stop(self):
        """Request recording to stop"""
        self.should_stop = True

    def run(self):
        """Execute the recording in a worker thread"""
        try:
            self.whisper_cli.start_recording()

            # Wait for stop signal or recording to end
            while self.whisper_cli.recording and not self.should_stop:
                import time
                time.sleep(0.1)

            # Stop recording and get transcription
            # This can take a while (30-60 seconds) depending on audio length and Whisper model performance
            self.status_update.emit("⏳ Stopping recording and processing audio... (this may take a minute)")

            import time
            import threading

            # Use a timeout wrapper to prevent indefinite hangs
            transcription = None
            transcription_error = None

            def transcribe_with_timeout():
                nonlocal transcription, transcription_error
                try:
                    transcription = self.whisper_cli.stop_recording()
                except Exception as e:
                    transcription_error = str(e)

            # Run transcription in a timeout thread (120 second timeout)
            timeout_seconds = 120
            transcribe_thread = threading.Thread(target=transcribe_with_timeout, daemon=True)
            transcribe_thread.start()
            transcribe_thread.join(timeout=timeout_seconds)

            if transcribe_thread.is_alive():
                # Transcription took too long
                self.error.emit(f"Transcription timeout after {timeout_seconds} seconds - Whisper model may be stuck")
                self.status_update.emit(f"❌ Transcription timeout after {timeout_seconds} seconds")
            elif transcription_error:
                self.error.emit(f"Transcription failed: {transcription_error}")
                self.status_update.emit(f"❌ Transcription error: {transcription_error}")
            elif transcription:
                self.result.emit(transcription)
            else:
                # No audio was recorded
                self.error.emit("No audio data was recorded")
                self.status_update.emit("❌ No audio data was recorded")

            self.stopped.emit()
            self.finished.emit()
        except Exception as e:
            error_msg = f"Recording error: {str(e)}"
            self.error.emit(error_msg)
            self.status_update.emit(error_msg)
            self.finished.emit()


class CodexWorker(QObject):
    """Worker thread for Claude CLI processing"""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(str, int)  # Emits (processed text, row index)

    def __init__(self, text: str, row_index: int = 0):
        super().__init__()
        self.text = text
        self.row_index = row_index

    def run(self):
        """Execute Claude processing in a worker thread"""
        try:
            # Create a strict prompt for Claude - demand only the output text
            prompt = f"""IMPORTANT: Return ONLY the processed text. No explanations, no preamble, no extra text.

Process this transcription:
- Highlight the most important keywords (up to 10% of text) with **keyword** format
- Fix any obvious typos
- Return ONLY the processed text, nothing else

Transcription:
{self.text}"""

            # Call Claude CLI directly (no filesystem exploration like codex exec does)
            process = subprocess.Popen(
                ["claude"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(input=prompt, timeout=60)

            if process.returncode == 0 and stdout:
                # Process the output - Claude might add some explanation, extract the relevant line
                output = stdout.strip()

                # Try to find the actual processed text (look for a line starting with capital letter that's not "Hi" alone)
                # Usually Claude's output has the processed text as the last substantial line
                lines = output.split('\n')

                # Find the line that looks like processed text (contains keywords with ** or has reasonable content)
                processed_text = None
                for line in reversed(lines):
                    line = line.strip()
                    if line and ('**' in line or (len(line) > 10 and any(c.isupper() for c in line))):
                        processed_text = line
                        break

                # If we found a good line, use it; otherwise use the whole output
                if processed_text:
                    self.result.emit(processed_text, self.row_index)
                else:
                    self.result.emit(output, self.row_index)
            else:
                error_msg = stderr if stderr else "Unknown error from Claude"
                self.error.emit(f"Claude processing failed: {error_msg}")

            self.finished.emit()
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except:
                pass
            self.error.emit("Claude processing timed out (exceeded 60 seconds).")
            self.finished.emit()
        except FileNotFoundError:
            self.error.emit("Claude CLI not found. Is it installed and in PATH?")
            self.finished.emit()
        except Exception as e:
            self.error.emit(f"Error processing with Claude: {str(e)}")
            self.finished.emit()


class WhisperGUI(QMainWindow):
    """Main GUI window for Whisper voice recording application"""

    def __init__(self, command_controller: Optional[CommandController] = None):
        super().__init__()
        self.setWindowTitle("Whisper Voice Recording")
        self.setGeometry(100, 100, 900, 600)

        # Initialize command controller (use FIFO by default if not provided)
        if command_controller is None:
            command_controller = FIFOCommandController(debug=False)
        self.command_controller = command_controller

        # Initialize Whisper CLI
        try:
            # Note: First run will download the Whisper model (~1.4GB)
            # This may take a few minutes - be patient!
            self.whisper = WhisperCLI(headless=True, debug=True)
        except Exception as e:
            error_msg = f"❌ Failed to initialize Whisper: {e}"
            print(error_msg)
            sys.exit(1)

        # History storage
        self.history_file = Path.home() / ".whisper" / "gui_history.json"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history: List[dict] = []
        self.load_history()

        # Recording state
        self.is_recording = False
        self.recording_thread = None

        # Row selection state
        self.selected_row = None  # Track which row is currently selected

        # Create lock file with GUI PID for hotkey daemon discovery
        self.lock_file = Path.home() / ".whisper" / "app.lock"
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.lock_file, 'w') as f:
                f.write(str(os.getpid()))
            print(f"✅ Created lock file with PID {os.getpid()}: {self.lock_file}")
        except Exception as e:
            print(f"⚠️ Could not create lock file: {e}")

        # Create signal emitter for safe thread-to-Qt communication
        # (used by IPC controller to dispatch commands to main thread)
        self.command_emitter = CommandSignalEmitter()
        self.command_emitter.toggle_signal.connect(self._on_toggle_command)
        self.command_emitter.start_signal.connect(self.start_recording)
        self.command_emitter.stop_signal.connect(self.stop_recording)

        # Start the command controller (handles IPC communication)
        try:
            # Wire up the controller callback to emit Qt signals
            self.command_controller.on_command_received = self._on_ipc_command
            self.command_controller.start()
            print(f"✅ Command controller started ({self.command_controller.__class__.__name__})")
        except Exception as e:
            print(f"❌ Error starting command controller: {e}")

        # Recording control is now handled via Unix signals (SIGUSR1/SIGUSR2/SIGALRM)
        # External programs can control recording via: whisper-recording-toggle toggle/start/stop
        # KDE shortcuts invoke whisper-recording-toggle, which sends signals to this process
        # This approach is Wayland-compatible and has zero dependencies

        # Setup UI
        self.setup_ui()
        self.refresh_history_table()

        # Setup system tray
        self.setup_tray()

    def setup_ui(self):
        """Create the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Title
        title = QLabel("🎤 Whisper Voice Recording")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)

        # Control buttons layout
        button_layout = QHBoxLayout()

        self.start_button = QPushButton("▶")
        self.start_button.setToolTip("Start Recording")
        self.start_button_style_normal = """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-width: 50px;
                min-height: 50px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """
        self.start_button_style_inactive = """
            QPushButton {
                background-color: #cccccc;
                color: #888888;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-width: 50px;
                min-height: 50px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #cccccc;
            }
        """
        self.start_button.setStyleSheet(self.start_button_style_normal)
        self.start_button.clicked.connect(self.start_recording)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("⏹")
        self.stop_button.setToolTip("Stop Recording")
        self.stop_button_style_inactive = """
            QPushButton {
                background-color: #cccccc;
                color: #888888;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-width: 50px;
                min-height: 50px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #cccccc;
            }
        """
        self.stop_button_style_active = """
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-width: 50px;
                min-height: 50px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #ba0000;
            }
        """
        self.stop_button.setStyleSheet(self.stop_button_style_inactive)
        self.stop_button.clicked.connect(self.stop_recording)
        button_layout.addWidget(self.stop_button)

        self.clear_button = QPushButton("🗑")
        self.clear_button.setToolTip("Clear History")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-width: 50px;
                min-height: 50px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
        """)
        self.clear_button.clicked.connect(self.clear_history)
        button_layout.addWidget(self.clear_button)

        self.codex_button = QPushButton("✨")
        self.codex_button.setToolTip("Process with Claude (highlight keywords & fix typos)")
        self.codex_button_style_normal = """
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-width: 50px;
                min-height: 50px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """
        self.codex_button_style_processing = """
            QPushButton {
                background-color: #cccccc;
                color: #888888;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-width: 50px;
                min-height: 50px;
                font-size: 24px;
            }
        """
        self.codex_button.setStyleSheet(self.codex_button_style_normal)
        self.codex_button.clicked.connect(self.on_codex_button_clicked)
        button_layout.addWidget(self.codex_button)

        self.terminal_button = QPushButton("💻")
        self.terminal_button.setToolTip("Open Terminal in Project Directory")
        self.terminal_button_style = """
            QPushButton {
                background-color: #1976D2;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-width: 50px;
                min-height: 50px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """
        self.terminal_button.setStyleSheet(self.terminal_button_style)
        self.terminal_button.clicked.connect(self.on_terminal_button_clicked)
        button_layout.addWidget(self.terminal_button)

        self.settings_button = QPushButton("⚙️")
        self.settings_button.setToolTip("Microphone Settings")
        self.settings_button_style = """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-width: 50px;
                min-height: 50px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """
        self.settings_button.setStyleSheet(self.settings_button_style)
        self.settings_button.clicked.connect(self.on_settings_button_clicked)
        button_layout.addWidget(self.settings_button)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # Status label
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)

        # History table
        history_label = QLabel("📝 Transcription History")
        history_font = QFont()
        history_font.setBold(True)
        history_label.setFont(history_font)
        main_layout.addWidget(history_label)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Timestamp", "Transcription", "Copy", "Lock"])
        self.history_table.setColumnWidth(0, 180)
        self.history_table.setColumnWidth(1, 550)
        self.history_table.setColumnWidth(2, 60)
        self.history_table.setColumnWidth(3, 60)
        # Enable word wrapping for multi-line text display
        self.history_table.setWordWrap(True)
        # Set minimum row height and enable resizing
        self.history_table.verticalHeader().setDefaultSectionSize(60)
        self.history_table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        # Connect row selection signal
        self.history_table.cellClicked.connect(self.on_table_cell_clicked)
        main_layout.addWidget(self.history_table)

        # Status bar
        self.statusBar().showMessage("Ready")

    def setup_tray(self):
        """Setup system tray icon and menu"""
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)

        # Store icon colors for later switching
        self.tray_icon_green = None
        self.tray_icon_red = None
        self.tray_icon_yellow = None

        # Try to set an icon - use a simple emoji-like icon or fallback to text
        try:
            # Create a simple icon using app icon
            from PyQt6.QtGui import QPixmap, QPainter, QColor

            # Green icon (ready state)
            pixmap_green = QPixmap(64, 64)
            pixmap_green.fill(QColor(255, 255, 255, 0))  # Transparent background
            painter = QPainter(pixmap_green)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            # Draw a simple microphone icon using circles and lines
            painter.setBrush(QColor(76, 175, 80))  # Green color
            painter.drawEllipse(16, 8, 32, 32)  # Mic circle
            painter.drawRect(26, 40, 12, 16)  # Mic stand
            painter.end()
            self.tray_icon_green = QIcon(pixmap_green)

            # Red icon (recording state)
            pixmap_red = QPixmap(64, 64)
            pixmap_red.fill(QColor(255, 255, 255, 0))  # Transparent background
            painter = QPainter(pixmap_red)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            # Draw a simple microphone icon using circles and lines
            painter.setBrush(QColor(244, 67, 54))  # Red color
            painter.drawEllipse(16, 8, 32, 32)  # Mic circle
            painter.drawRect(26, 40, 12, 16)  # Mic stand
            painter.end()
            self.tray_icon_red = QIcon(pixmap_red)

            # Yellow icon (pause/transcribing state)
            pixmap_yellow = QPixmap(64, 64)
            pixmap_yellow.fill(QColor(255, 255, 255, 0))  # Transparent background
            painter = QPainter(pixmap_yellow)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            # Draw a simple microphone icon using circles and lines
            painter.setBrush(QColor(255, 193, 7))  # Yellow color (Material Design Amber)
            painter.drawEllipse(16, 8, 32, 32)  # Mic circle
            painter.drawRect(26, 40, 12, 16)  # Mic stand
            painter.end()
            self.tray_icon_yellow = QIcon(pixmap_yellow)

            # Set initial green icon
            self.tray_icon.setIcon(self.tray_icon_green)
        except:
            # Fallback: just use text
            pass

        # Create tray menu
        tray_menu = QMenu()

        # Show/Hide action
        show_action = tray_menu.addAction("Show/Hide")
        show_action.triggered.connect(self.toggle_window)

        # Recording status
        tray_menu.addSeparator()
        self.tray_status = tray_menu.addAction("🎤 Ready")
        self.tray_status.setEnabled(False)

        # Start recording action
        tray_menu.addSeparator()
        start_action = tray_menu.addAction("▶ Start Recording")
        start_action.triggered.connect(self.start_recording)

        # Stop recording action
        stop_action = tray_menu.addAction("⏹ Stop Recording")
        stop_action.triggered.connect(self.stop_recording)

        # Exit action
        tray_menu.addSeparator()
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(self.exit_app)

        self.tray_icon.setContextMenu(tray_menu)

        # Show the tray icon
        self.tray_icon.show()

        # Connect to window state changes
        self.tray_icon.activated.connect(self.tray_icon_activated)

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

    def _set_tray_icon_yellow(self):
        """Change tray icon to yellow (pause/transcribing state)"""
        if self.tray_icon_yellow:
            self.tray_icon.setIcon(self.tray_icon_yellow)

    def _set_tray_icon_green(self):
        """Change tray icon to green (ready state)"""
        if self.tray_icon_green:
            self.tray_icon.setIcon(self.tray_icon_green)

    def exit_app(self):
        """Exit the application completely"""
        if self.is_recording:
            self.stop_recording()

        # Clean up threads if they're still running
        if self.recording_thread and self.recording_thread.isRunning():
            self.recording_thread.quit()
            self.recording_thread.wait()

        # Stop the IPC command controller
        try:
            if hasattr(self, 'command_controller') and self.command_controller:
                self.command_controller.stop()
                print("✅ Command controller stopped")
        except Exception as e:
            print(f"⚠️  Error stopping command controller: {e}")

        # Hide tray icon and cleanup
        self.tray_icon.hide()

        # Cleanup Whisper resources
        self.whisper.cleanup()

        # Exit the application via sys.exit (bypasses closeEvent)
        sys.exit(0)

    def _on_toggle_command(self):
        """Handle toggle command - dynamically choose start or stop based on current state"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def _on_ipc_command(self, command: str):
        """Handle command received from IPC controller.

        This callback is invoked by the command controller when a command is received.
        We emit Qt signals to safely invoke methods in the main GUI thread.

        Args:
            command: Command string ("start", "stop", or "toggle")
        """
        sys.stderr.write(f"🔔 Received IPC command: {command}\n")
        sys.stderr.flush()

        # Emit Qt signals to safely invoke recording methods in the main thread
        if command == "toggle":
            self.command_emitter.toggle_signal.emit()
        elif command == "start":
            self.command_emitter.start_signal.emit()
        elif command == "stop":
            self.command_emitter.stop_signal.emit()
        else:
            sys.stderr.write(f"❌ Unknown command: {command}\n")
            sys.stderr.flush()

    def on_terminal_button_clicked(self):
        """Open Xfce terminal in the Whisper project directory"""
        import shutil

        # Get the project directory (where this script is located)
        project_dir = str(Path(__file__).parent.absolute())

        # List of terminal commands to try (with full paths and fallbacks)
        terminal_commands = [
            (["/usr/bin/xfce4-terminal", "--working-directory", project_dir], "xfce4-terminal"),
            (["xfce4-terminal", "--working-directory", project_dir], "xfce4-terminal"),
            (["/usr/bin/konsole", "-e", f"bash -c 'cd {project_dir} && bash'"], "konsole"),
            (["konsole", "-e", f"bash -c 'cd {project_dir} && bash'"], "konsole"),
            (["/usr/bin/gnome-terminal", "--working-directory", project_dir], "gnome-terminal"),
            (["gnome-terminal", "--working-directory", project_dir], "gnome-terminal"),
            (["/usr/bin/xterm", "-e", f"cd {project_dir}; bash"], "xterm"),
            (["xterm", "-e", f"cd {project_dir}; bash"], "xterm"),
        ]

        terminal_found = False
        for cmd, name in terminal_commands:
            try:
                subprocess.Popen(cmd, start_new_session=True)
                self.statusBar().showMessage(f"📂 Terminal ({name}) opened in: {project_dir}")
                terminal_found = True
                break
            except (FileNotFoundError, OSError):
                continue

        if not terminal_found:
            error_msg = "❌ No terminal found (tried xfce4-terminal, konsole, gnome-terminal, xterm)"
            self.statusBar().showMessage(error_msg)
            self.status_label.setText(error_msg)

    def on_settings_button_clicked(self):
        """Open microphone settings dialog"""
        from PyQt6.QtWidgets import QComboBox, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

        # Get available input devices
        try:
            input_devices = []
            device_names = []

            for i in range(self.whisper.audio.get_device_count()):
                try:
                    device_info = self.whisper.audio.get_device_info_by_index(i)
                    if device_info['maxInputChannels'] > 0:
                        input_devices.append(i)
                        device_names.append(device_info['name'])
                except:
                    continue

            if not input_devices:
                self.status_label.setText("❌ No input devices found")
                return

            # Create settings dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Microphone Settings")
            dialog.setGeometry(200, 200, 500, 150)

            layout = QVBoxLayout(dialog)

            # Label
            label = QLabel("Select microphone input device:")
            layout.addWidget(label)

            # Dropdown
            combo = QComboBox()
            combo.addItems(device_names)

            # Load current selection
            current_device = self.whisper.input_device_index
            if current_device is not None and current_device in input_devices:
                combo.setCurrentIndex(input_devices.index(current_device))

            layout.addWidget(combo)

            # Buttons
            button_layout = QHBoxLayout()

            ok_button = QPushButton("OK")
            cancel_button = QPushButton("Cancel")

            def save_settings():
                selected_index = combo.currentIndex()
                device_idx = input_devices[selected_index]

                # Save to config
                import json
                config_file = os.path.expanduser("~/.whisper/config")
                config = {"input_device_index": device_idx}
                os.makedirs(os.path.dirname(config_file), exist_ok=True)
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)

                # Update whisper instance
                self.whisper.input_device_index = device_idx

                self.status_label.setText(f"✅ Microphone set to: {device_names[selected_index]}")
                self.statusBar().showMessage("Microphone settings saved")
                dialog.accept()

            ok_button.clicked.connect(save_settings)
            cancel_button.clicked.connect(dialog.reject)

            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            dialog.exec()

        except Exception as e:
            self.status_label.setText(f"❌ Error: {str(e)}")
            self.statusBar().showMessage("Failed to access audio devices")

    def start_recording(self):
        """Start recording"""
        if self.is_recording:
            self.status_label.setText("⚠️ Already recording...")
            return

        self.is_recording = True
        # Gray out start button and activate stop button
        self.start_button.setStyleSheet(self.start_button_style_inactive)
        self.start_button.setEnabled(False)
        self.stop_button.setStyleSheet(self.stop_button_style_active)
        self.stop_button.setEnabled(True)
        self.status_label.setText("🎤 Recording... (Press Stop when done)")
        self.statusBar().showMessage("Recording in progress...")
        # Update tray status and icon
        self.tray_status.setText("🎤 Recording...")
        self._set_tray_icon_red()  # Change icon to red when recording starts

        # Start recording in a worker thread
        self.recording_worker = RecordingWorker(self.whisper)
        self.recording_thread = QThread()

        self.recording_worker.moveToThread(self.recording_thread)
        self.recording_thread.started.connect(self.recording_worker.run)
        self.recording_worker.finished.connect(self.on_recording_finished)
        self.recording_worker.result.connect(self.on_recording_result)
        self.recording_worker.error.connect(self.on_recording_error)
        self.recording_worker.status_update.connect(self.on_recording_status_update)

        self.recording_thread.start()

    def stop_recording(self):
        """Stop recording"""
        if not self.is_recording or not hasattr(self, 'recording_worker'):
            return

        self.recording_worker.stop()
        self.status_label.setText("⏳ Processing transcription...")
        self.stop_button.setEnabled(False)


    def on_recording_finished(self):
        """Handle recording completion"""
        self.is_recording = False
        # Restore start button and gray out stop button
        self.start_button.setStyleSheet(self.start_button_style_normal)
        self.start_button.setEnabled(True)
        self.stop_button.setStyleSheet(self.stop_button_style_inactive)
        # Update tray status and icon
        self.tray_status.setText("🎤 Ready")
        self._set_tray_icon_green()  # Change icon back to green when transcription is done
        self.recording_thread.quit()
        self.recording_thread.wait()

    def on_recording_result(self, transcription: str):
        """Handle successful transcription"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        transcription_text = transcription.strip()

        # Add to history
        item = {
            "timestamp": timestamp,
            "text": transcription_text,
            "protected": False  # New recordings are not protected by default
        }
        self.history.insert(0, item)  # Add to beginning for newest first
        self.save_history()

        # Deselect any previously selected row when new recording is made
        self.selected_row = None

        # Automatically copy to clipboard
        self._copy_text_to_clipboard(transcription_text)

        self.status_label.setText(f"✅ Copied to clipboard: \"{transcription_text[:50]}...\"")
        self.statusBar().showMessage("✅ Transcription copied to clipboard")

        # Auto-paste transcription to focused window
        # Tries multiple paste methods for maximum compatibility:
        # 1. Shift+Insert (universal X11 paste)
        # 2. Ctrl+V (standard paste)
        # 3. Ctrl+Shift+V (some apps like terminals)
        try:
            import subprocess
            import os
            import time

            # Debug logging: show X11 environment
            display = os.environ.get('DISPLAY', 'NOT SET')
            xauth = os.environ.get('XAUTHORITY', 'NOT SET')
            print(f"🔍 Auto-paste X11 env: DISPLAY={display}, XAUTHORITY={xauth}")

            # Add small delay to ensure focus is stable
            time.sleep(0.2)

            # Try multiple paste methods for better compatibility
            paste_methods = [
                (['xdotool', 'key', 'shift+Insert'], "Shift+Insert"),
                (['xdotool', 'key', 'ctrl+v'], "Ctrl+V"),
                (['xdotool', 'key', 'ctrl+shift+v'], "Ctrl+Shift+V"),
            ]

            pasted = False
            for cmd, method_name in paste_methods:
                try:
                    result = subprocess.run(
                        cmd,
                        check=False,
                        timeout=1,
                        capture_output=True,
                        text=True
                    )

                    if result.returncode == 0:
                        print(f"📋 Auto-pasted with {method_name}")
                        pasted = True
                        break
                except subprocess.TimeoutExpired:
                    continue
                except Exception as e:
                    continue

            if not pasted:
                print("⚠️ All paste methods failed (window may not have focus)")

        except Exception as e:
            print(f"⚠️ Auto-paste failed (non-critical): {e}")
            # Don't fail the transcription - this is just a convenience feature

        self.refresh_history_table()

    def on_recording_error(self, error_msg: str):
        """Handle recording error"""
        self.status_label.setText(f"❌ Error: {error_msg}")
        self.statusBar().showMessage("Error during recording")

    def on_recording_status_update(self, status: str):
        """Handle status updates from recording worker"""
        self.status_label.setText(status)
        self.statusBar().showMessage(status)

        # Change icon to yellow when recording pauses and transcription begins
        if "Stopping recording" in status or "processing audio" in status.lower():
            self._set_tray_icon_yellow()

    def refresh_history_table(self):
        """Refresh the history table display"""
        self.history_table.setRowCount(len(self.history))

        for row, item in enumerate(self.history):
            # Timestamp column
            timestamp_item = QTableWidgetItem(item["timestamp"])
            timestamp_item.setFlags(timestamp_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.history_table.setItem(row, 0, timestamp_item)

            # Transcription column - use a clickable label with HTML rich text to render bold formatting
            html_text = markdown_to_html(item["text"])
            text_label = ClickableLabel(html_text, row)
            text_label.setWordWrap(True)
            text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            # Connect to a wrapper that converts (row) to (row, column)
            text_label.clicked.connect(lambda r: self.on_table_cell_clicked(r, 1))
            self.history_table.setCellWidget(row, 1, text_label)

            # Copy button column
            copy_button = QPushButton("Copy")
            copy_button.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #0b7dda;
                }
            """)
            copy_button.clicked.connect(lambda checked, r=row: self.copy_to_clipboard(r))
            self.history_table.setCellWidget(row, 2, copy_button)

            # Lock/Delete button column - shows delete if row is selected, lock otherwise
            if self.selected_row == row:
                # Show delete button for selected row (overrides protection)
                delete_button = QPushButton("🗑 Delete")
                delete_button.setToolTip("Delete this item (overrides protection)")
                delete_button.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        padding: 5px;
                        border-radius: 3px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #da190b;
                    }
                    QPushButton:pressed {
                        background-color: #ba0000;
                    }
                """)
                delete_button.clicked.connect(lambda checked, r=row: self.delete_history_item(r))
                self.history_table.setCellWidget(row, 3, delete_button)
            else:
                # Show lock/unlock button for unselected rows
                is_protected = item.get("protected", False)
                lock_button = QPushButton("🔓" if is_protected else "🔒")
                lock_button.setToolTip("Protected - Click to unprotect" if is_protected else "Unprotected - Click to protect")
                lock_button.setStyleSheet("""
                    QPushButton {
                        background-color: """ + ("#FF9800" if is_protected else "#999999") + """;
                        color: white;
                        padding: 5px;
                        border-radius: 3px;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: """ + ("#FFB74D" if is_protected else "#666666") + """;
                    }
                """)
                lock_button.clicked.connect(lambda checked, r=row: self.toggle_protection(r))
                self.history_table.setCellWidget(row, 3, lock_button)

    def _copy_text_to_clipboard(self, text: str) -> bool:
        """
        Copy text to clipboard (helper method)

        Args:
            text: Text to copy

        Returns:
            True if successful, False otherwise
        """
        try:
            if os.environ.get("WAYLAND_DISPLAY"):
                # Wayland: wl-copy handles both selections
                process = subprocess.Popen(
                    ["wl-copy"],
                    stdin=subprocess.PIPE,
                    text=True
                )
                process.communicate(input=text)
            else:
                # X11: Set BOTH PRIMARY (for Shift+Insert) and CLIPBOARD (for Ctrl+V)
                # PRIMARY selection - used by Shift+Insert paste
                process = subprocess.Popen(
                    ["xclip", "-selection", "primary"],
                    stdin=subprocess.PIPE,
                    text=True
                )
                process.communicate(input=text)

                # CLIPBOARD selection - used by Ctrl+V paste
                process = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                    text=True
                )
                process.communicate(input=text)

            return True
        except FileNotFoundError:
            self.statusBar().showMessage("❌ Clipboard tool not found (wl-copy or xclip)")
            return False
        except Exception as e:
            self.statusBar().showMessage(f"❌ Copy failed: {str(e)}")
            return False

    def copy_to_clipboard(self, row: int):
        """Copy history item to clipboard"""
        if row < len(self.history):
            text = self.history[row]["text"]
            if self._copy_text_to_clipboard(text):
                self.statusBar().showMessage(f"✅ Copied to clipboard: {text[:40]}...")

    def toggle_protection(self, row: int):
        """Toggle delete protection for a history item"""
        if row < len(self.history):
            item = self.history[row]
            is_protected = item.get("protected", False)
            item["protected"] = not is_protected
            self.save_history()
            self.refresh_history_table()

            status = "🔒 Protected" if item["protected"] else "🔓 Unprotected"
            text_preview = item["text"][:40]
            self.statusBar().showMessage(f"{status}: {text_preview}...")

    def on_table_cell_clicked(self, row: int, column: int):
        """Handle table cell clicks to select rows"""
        # Clicking on any cell in a row selects that row
        if self.selected_row == row:
            # Clicking the selected row again deselects it
            self.selected_row = None
            self.statusBar().showMessage("Row deselected")
        else:
            # Select the new row
            self.selected_row = row
            text_preview = self.history[row]["text"][:50] if row < len(self.history) else ""
            self.statusBar().showMessage(f"Row selected (click delete button to remove): {text_preview}...")

        self.refresh_history_table()

    def delete_history_item(self, row: int):
        """Delete a history item, overriding protection"""
        if row < len(self.history):
            deleted_item = self.history.pop(row)
            self.save_history()
            self.selected_row = None  # Deselect after deletion
            self.refresh_history_table()

            text_preview = deleted_item["text"][:40]
            self.statusBar().showMessage(f"🗑 Deleted: {text_preview}...")
            self.status_label.setText(f"✅ Item deleted: {text_preview}...")

    def clear_history(self):
        """Clear all history except protected items"""
        # Keep only protected items
        protected_items = [item for item in self.history if item.get("protected", False)]
        deleted_count = len(self.history) - len(protected_items)
        self.history = protected_items
        self.save_history()
        self.refresh_history_table()

        if deleted_count > 0:
            if protected_items:
                self.status_label.setText(f"🗑 Deleted {deleted_count} items ({len(protected_items)} protected)")
                self.statusBar().showMessage(f"History cleared: {deleted_count} deleted, {len(protected_items)} protected items retained")
            else:
                self.status_label.setText("🗑 History cleared")
                self.statusBar().showMessage("History cleared")
        else:
            self.status_label.setText("🔒 All items are protected")
            self.statusBar().showMessage("Cannot clear history: all items are protected")

    def load_history(self):
        """Load history from file"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load history: {e}")
            self.history = []

    def save_history(self):
        """Save history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save history: {e}")

    def on_codex_button_clicked(self):
        """Handle codex processing button click"""
        # If a row is selected, process that item
        if self.selected_row is not None and self.selected_row < len(self.history):
            text_to_process = self.history[self.selected_row]["text"]
            row_to_update = self.selected_row
        else:
            # Otherwise, use the most recent transcription
            if self.history:
                text_to_process = self.history[0]["text"]
                row_to_update = 0
            else:
                self.statusBar().showMessage("❌ No transcriptions to process")
                return

        # Start codex processing
        self.status_label.setText("⏳ Processing with Claude...")
        self.codex_button.setStyleSheet(self.codex_button_style_processing)
        self.codex_button.setEnabled(False)

        # Start processing in a worker thread
        self.codex_worker = CodexWorker(text_to_process, row_to_update)
        self.codex_thread = QThread()

        self.codex_worker.moveToThread(self.codex_thread)
        self.codex_thread.started.connect(self.codex_worker.run)
        self.codex_worker.finished.connect(self.on_codex_finished)
        self.codex_worker.result.connect(self.on_codex_result)
        self.codex_worker.error.connect(self.on_codex_error)

        self.codex_thread.start()

    def on_codex_result(self, processed_text: str, row_index: int):
        """Handle successful codex processing"""
        # Update the history with the processed text
        if row_index < len(self.history):
            self.history[row_index]["text"] = processed_text
            # Save the updated history
            self.save_history()
            # Refresh the table to show the updated text
            self.refresh_history_table()

        # Copy the processed text to clipboard
        self._copy_text_to_clipboard(processed_text)

        self.status_label.setText(f"✨ Processed with Claude (copied to clipboard)")
        self.statusBar().showMessage("✨ Claude processing complete - transcription updated")

    def on_codex_error(self, error_msg: str):
        """Handle codex processing error"""
        self.status_label.setText(f"❌ Error: {error_msg}")
        self.statusBar().showMessage(f"❌ Claude error: {error_msg}")

    def on_codex_finished(self):
        """Handle codex processing completion"""
        self.codex_button.setStyleSheet(self.codex_button_style_normal)
        self.codex_button.setEnabled(True)
        self.codex_thread.quit()
        self.codex_thread.wait()

    def closeEvent(self, event):
        """Handle window close - minimize to tray instead of exiting"""
        # If recording is active, stop it properly using the GUI method (not direct Whisper call)
        if self.is_recording:
            self.stop_recording()

        # Wait for recording thread to finish before hiding window
        # This prevents X11/Wayland crashes during window hide
        if self.recording_thread and self.recording_thread.isRunning():
            self.recording_thread.quit()
            self.recording_thread.wait()

        # IMPORTANT: Do NOT delete lock file here - it should only be deleted on actual app exit
        # The lock file indicates the GUI is still running in the system tray
        # Only exit_app() and main's finally block should delete the lock file

        # Just hide the window, don't exit the app
        # The app continues running in the system tray
        self.hide()
        event.ignore()  # Ignore the close event to prevent app exit


def main():
    # Singleton check - prevent multiple instances
    import fcntl
    lock_file_path = os.path.expanduser("~/.whisper/app.lock")
    os.makedirs(os.path.dirname(lock_file_path), exist_ok=True)

    try:
        lock_file = open(lock_file_path, 'w')
        # Try to acquire exclusive lock (non-blocking)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        # Another instance is already running
        print("❌ Whisper GUI is already running!")
        print("Only one instance can run at a time.")
        sys.exit(1)

    # Write PID to lock file
    lock_file.write(str(os.getpid()))
    lock_file.flush()

    app = QApplication(sys.argv)
    window = WhisperGUI()
    window.show()

    # Handle Ctrl+C (SIGINT) to gracefully exit
    def handle_sigint(signum, frame):
        print("\n👋 Exiting...")
        window.close()
        app.quit()

    signal.signal(signal.SIGINT, handle_sigint)

    try:
        sys.exit(app.exec())
    finally:
        # Release lock on exit
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
            os.remove(lock_file_path)
        except:
            pass


if __name__ == "__main__":
    main()
