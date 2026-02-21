#!/usr/bin/env python3
"""
Whisper GUI - A minimal PyQt6 application for voice recording with history buffer
"""

import sys
import json
import os
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QTableWidget, QTableWidgetItem, QLabel, QStatusBar
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
    from PyQt6.QtGui import QColor, QFont
except ImportError:
    print("❌ PyQt6 is not installed!")
    print("Install with: pip install PyQt6")
    sys.exit(1)

from whisper_cli import WhisperCLI


class RecordingWorker(QObject):
    """Worker thread for non-blocking recording operations"""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(str)  # Emits the transcribed text
    stopped = pyqtSignal()

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
            transcription = self.whisper_cli.stop_recording()

            if transcription:
                self.result.emit(transcription)

            self.stopped.emit()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()


class WhisperGUI(QMainWindow):
    """Main GUI window for Whisper voice recording application"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Whisper Voice Recording")
        self.setGeometry(100, 100, 900, 600)

        # Initialize Whisper CLI
        try:
            self.whisper = WhisperCLI(headless=True, debug=False)
        except Exception as e:
            print(f"❌ Failed to initialize Whisper: {e}")
            sys.exit(1)

        # History storage
        self.history_file = Path.home() / ".whisper" / "gui_history.json"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history: List[dict] = []
        self.load_history()

        # Recording state
        self.is_recording = False
        self.recording_thread = None

        # Setup UI
        self.setup_ui()
        self.refresh_history_table()

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

        self.start_button = QPushButton("▶ Start Recording")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.start_button.clicked.connect(self.start_recording)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("⏹ Stop Recording")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #ba0000;
            }
        """)
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        self.clear_button = QPushButton("🗑 Clear History")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
        """)
        self.clear_button.clicked.connect(self.clear_history)
        button_layout.addWidget(self.clear_button)

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
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(["Timestamp", "Transcription", "Copy"])
        self.history_table.setColumnWidth(0, 180)
        self.history_table.setColumnWidth(1, 550)
        self.history_table.setColumnWidth(2, 80)
        main_layout.addWidget(self.history_table)

        # Status bar
        self.statusBar().showMessage("Ready")

    def start_recording(self):
        """Start recording"""
        if self.is_recording:
            self.status_label.setText("⚠️ Already recording...")
            return

        self.is_recording = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("🎤 Recording... (Press Stop when done)")
        self.statusBar().showMessage("Recording in progress...")

        # Start recording in a worker thread
        self.recording_worker = RecordingWorker(self.whisper)
        self.recording_thread = QThread()

        self.recording_worker.moveToThread(self.recording_thread)
        self.recording_thread.started.connect(self.recording_worker.run)
        self.recording_worker.finished.connect(self.on_recording_finished)
        self.recording_worker.result.connect(self.on_recording_result)
        self.recording_worker.error.connect(self.on_recording_error)

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
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.recording_thread.quit()
        self.recording_thread.wait()

    def on_recording_result(self, transcription: str):
        """Handle successful transcription"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Add to history
        item = {
            "timestamp": timestamp,
            "text": transcription.strip()
        }
        self.history.insert(0, item)  # Add to beginning for newest first
        self.save_history()

        self.status_label.setText(f"✅ Saved: \"{transcription.strip()[:50]}...\"")
        self.statusBar().showMessage("Transcription saved")

        self.refresh_history_table()

    def on_recording_error(self, error_msg: str):
        """Handle recording error"""
        self.status_label.setText(f"❌ Error: {error_msg}")
        self.statusBar().showMessage("Error during recording")

    def refresh_history_table(self):
        """Refresh the history table display"""
        self.history_table.setRowCount(len(self.history))

        for row, item in enumerate(self.history):
            # Timestamp column
            timestamp_item = QTableWidgetItem(item["timestamp"])
            timestamp_item.setFlags(timestamp_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.history_table.setItem(row, 0, timestamp_item)

            # Transcription column
            text_item = QTableWidgetItem(item["text"])
            text_item.setFlags(text_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.history_table.setItem(row, 1, text_item)

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

    def copy_to_clipboard(self, row: int):
        """Copy history item to clipboard"""
        if row < len(self.history):
            text = self.history[row]["text"]

            # Use xclip or wl-copy depending on display server
            try:
                if os.environ.get("WAYLAND_DISPLAY"):
                    process = subprocess.Popen(
                        ["wl-copy"],
                        stdin=subprocess.PIPE,
                        text=True
                    )
                else:
                    process = subprocess.Popen(
                        ["xclip", "-selection", "clipboard"],
                        stdin=subprocess.PIPE,
                        text=True
                    )

                process.communicate(input=text)
                self.statusBar().showMessage(f"✅ Copied to clipboard: {text[:40]}...")
            except FileNotFoundError:
                self.statusBar().showMessage("❌ Clipboard tool not found (wl-copy or xclip)")
            except Exception as e:
                self.statusBar().showMessage(f"❌ Copy failed: {str(e)}")

    def clear_history(self):
        """Clear all history"""
        self.history = []
        self.save_history()
        self.refresh_history_table()
        self.status_label.setText("🗑 History cleared")
        self.statusBar().showMessage("History cleared")

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

    def closeEvent(self, event):
        """Handle application close"""
        if self.is_recording:
            self.whisper.stop_recording()

        if self.recording_thread and self.recording_thread.isRunning():
            self.recording_thread.quit()
            self.recording_thread.wait()

        self.whisper.cleanup()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = WhisperGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
