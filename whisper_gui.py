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
    from PyQt6.QtWidgets import QHeaderView
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

        # Row selection state
        self.selected_row = None  # Track which row is currently selected

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
        # Restore start button and gray out stop button
        self.start_button.setStyleSheet(self.start_button_style_normal)
        self.start_button.setEnabled(True)
        self.stop_button.setStyleSheet(self.stop_button_style_inactive)
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

    # Handle Ctrl+C (SIGINT) to gracefully exit
    def handle_sigint(signum, frame):
        print("\n👋 Exiting...")
        window.close()
        app.quit()

    signal.signal(signal.SIGINT, handle_sigint)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
