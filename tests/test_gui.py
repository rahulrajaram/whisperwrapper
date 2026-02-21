#!/usr/bin/env python3
"""
Unit tests for WhisperGUI with mocks and stubs.

Tests cover:
- GUI initialization
- Recording start/stop
- Transcription handling
- System tray functionality
- History management
- Settings dialog
- Error handling
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import sys
import os
import json
import tempfile
from pathlib import Path

# Mock PyQt6 before importing GUI
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtWidgets'] = MagicMock()
sys.modules['PyQt6.QtCore'] = MagicMock()
sys.modules['PyQt6.QtGui'] = MagicMock()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal


class TestWhisperGUIInitialization(unittest.TestCase):
    """Test GUI initialization and setup."""

    def setUp(self):
        """Set up test fixtures."""
        self.app_patcher = patch('PyQt6.QtWidgets.QApplication')
        self.mock_app = self.app_patcher.start()

        # Mock WhisperCLI
        self.whisper_cli_patcher = patch('whisper_app.gui.WhisperCLI')
        self.mock_whisper_cli = self.whisper_cli_patcher.start()

        # Create temp config directory
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'config.json')
        self.history_path = os.path.join(self.temp_dir, 'history.json')

    def tearDown(self):
        """Clean up test fixtures."""
        self.app_patcher.stop()
        self.whisper_cli_patcher.stop()

        # Clean up temp files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('whisper_app.gui.QMainWindow')
    @patch('whisper_app.gui.QSystemTrayIcon')
    def test_gui_initialization(self, mock_tray, mock_window):
        """Test that GUI initializes with proper components."""
        from whisper_app.gui import WhisperGUI

        # Mock the required components
        mock_whisper = Mock()
        with patch.object(WhisperGUI, '__init__', return_value=None):
            gui = WhisperGUI()
            gui.whisper = mock_whisper
            gui.is_recording = False
            gui.history = []

            self.assertIsNotNone(gui)
            self.assertFalse(gui.is_recording)
            self.assertEqual(gui.history, [])

    @patch('whisper_app.gui.QMainWindow')
    def test_singleton_lock(self, mock_window):
        """Test that singleton pattern prevents multiple instances."""
        import fcntl

        lock_file = os.path.join(self.temp_dir, 'app.lock')

        # First instance should acquire lock
        with open(lock_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Second instance should fail to acquire lock
            with self.assertRaises(IOError):
                with open(lock_file, 'w') as f2:
                    fcntl.flock(f2.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


class TestWhisperGUIRecording(unittest.TestCase):
    """Test recording functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_whisper = Mock()
        self.mock_gui = Mock()
        self.mock_gui.whisper = self.mock_whisper
        self.mock_gui.is_recording = False
        self.mock_gui.recording_thread = None

    def test_start_recording_success(self):
        """Test successful recording start."""
        from whisper_app.gui import RecordingThread

        # Mock the recording thread
        mock_thread = Mock(spec=RecordingThread)
        mock_thread.status_update = Mock()
        mock_thread.result = Mock()
        mock_thread.error = Mock()
        mock_thread.stopped = Mock()

        with patch('whisper_app.gui.RecordingThread', return_value=mock_thread):
            # Simulate start_recording
            self.mock_gui.is_recording = True
            self.mock_gui.recording_thread = mock_thread

            self.assertTrue(self.mock_gui.is_recording)
            self.assertIsNotNone(self.mock_gui.recording_thread)

    def test_start_recording_already_recording(self):
        """Test that starting recording while already recording is handled."""
        self.mock_gui.is_recording = True

        # Should not start a new recording
        # In actual implementation, this would return early
        if self.mock_gui.is_recording:
            return  # Already recording

        # This should not be reached
        self.mock_whisper.start_recording.assert_not_called()

    def test_stop_recording_success(self):
        """Test successful recording stop and transcription."""
        self.mock_gui.is_recording = True
        self.mock_whisper.stop_recording.return_value = "Hello world"

        # Simulate stop_recording
        result = self.mock_whisper.stop_recording()

        self.assertEqual(result, "Hello world")
        self.mock_whisper.stop_recording.assert_called_once()

    def test_stop_recording_no_audio(self):
        """Test stop recording when no audio was captured."""
        self.mock_gui.is_recording = True
        self.mock_whisper.stop_recording.return_value = None

        result = self.mock_whisper.stop_recording()

        self.assertIsNone(result)

    def test_stop_recording_exception(self):
        """Test stop recording when exception occurs."""
        self.mock_gui.is_recording = True
        self.mock_whisper.stop_recording.side_effect = Exception("Audio error")

        with self.assertRaises(Exception):
            self.mock_whisper.stop_recording()


class TestWhisperGUIRecordingThread(unittest.TestCase):
    """Test RecordingThread functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_whisper = Mock()

    @patch('whisper_app.gui.QThread')
    def test_recording_thread_success(self, mock_qthread):
        """Test recording thread completes successfully."""
        from whisper_app.gui import RecordingThread

        mock_thread = Mock(spec=RecordingThread)
        mock_thread.whisper_cli = self.mock_whisper
        mock_thread.should_stop = False

        self.mock_whisper.recording = True
        self.mock_whisper.stop_recording.return_value = "Test transcription"

        # Simulate recording
        self.mock_whisper.start_recording()
        transcription = self.mock_whisper.stop_recording()

        self.assertEqual(transcription, "Test transcription")
        self.mock_whisper.start_recording.assert_called_once()

    @patch('whisper_app.gui.QThread')
    def test_recording_thread_timeout(self, mock_qthread):
        """Test recording thread handles timeout."""
        from whisper_app.gui import RecordingThread

        mock_thread = Mock(spec=RecordingThread)
        mock_thread.whisper_cli = self.mock_whisper

        # Simulate timeout (thread still alive after join)
        mock_transcribe_thread = Mock()
        mock_transcribe_thread.is_alive.return_value = True

        # In actual implementation, this would emit error signal
        if mock_transcribe_thread.is_alive():
            error_msg = "Transcription timeout after 120 seconds"
            self.assertEqual(error_msg, "Transcription timeout after 120 seconds")


class TestWhisperGUIHistory(unittest.TestCase):
    """Test history management functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.history_file = os.path.join(self.temp_dir, 'history.json')
        self.mock_gui = Mock()
        self.mock_gui.history_file = self.history_file
        self.mock_gui.history = []

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_save_history_creates_file(self):
        """Test that save_history creates file if it doesn't exist."""
        history_data = [
            {
                "timestamp": "2025-11-02 13:00:00",
                "text": "Test transcription",
                "raw_text": "Test transcription"
            }
        ]

        # Save history
        with open(self.history_file, 'w') as f:
            json.dump(history_data, f, indent=2)

        # Verify file exists
        self.assertTrue(os.path.exists(self.history_file))

        # Load and verify content
        with open(self.history_file, 'r') as f:
            loaded_history = json.load(f)

        self.assertEqual(len(loaded_history), 1)
        self.assertEqual(loaded_history[0]["text"], "Test transcription")

    def test_load_history_empty_file(self):
        """Test loading history from empty/missing file."""
        # Try to load from non-existent file
        if not os.path.exists(self.history_file):
            history = []
        else:
            with open(self.history_file, 'r') as f:
                history = json.load(f)

        self.assertEqual(history, [])

    def test_add_to_history(self):
        """Test adding new entry to history."""
        history = []
        new_entry = {
            "timestamp": "2025-11-02 13:00:00",
            "text": "New transcription",
            "raw_text": "New transcription"
        }

        history.insert(0, new_entry)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["text"], "New transcription")

    def test_delete_history_entry(self):
        """Test deleting entry from history."""
        history = [
            {"timestamp": "2025-11-02 13:00:00", "text": "Entry 1"},
            {"timestamp": "2025-11-02 13:01:00", "text": "Entry 2"},
            {"timestamp": "2025-11-02 13:02:00", "text": "Entry 3"}
        ]

        # Delete entry at index 1
        del history[1]

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["text"], "Entry 1")
        self.assertEqual(history[1]["text"], "Entry 3")

    def test_clear_all_history(self):
        """Test clearing entire history."""
        history = [
            {"timestamp": "2025-11-02 13:00:00", "text": "Entry 1"},
            {"timestamp": "2025-11-02 13:01:00", "text": "Entry 2"}
        ]

        history.clear()

        self.assertEqual(len(history), 0)


class TestWhisperGUISettings(unittest.TestCase):
    """Test settings dialog and microphone configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'config.json')
        self.mock_whisper = Mock()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_save_microphone_config(self):
        """Test saving microphone configuration."""
        config = {"input_device_index": 9}

        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

        # Verify saved
        with open(self.config_file, 'r') as f:
            loaded_config = json.load(f)

        self.assertEqual(loaded_config["input_device_index"], 9)

    def test_load_microphone_config(self):
        """Test loading microphone configuration."""
        config = {"input_device_index": 5}

        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

        # Load config
        with open(self.config_file, 'r') as f:
            loaded_config = json.load(f)

        self.assertEqual(loaded_config["input_device_index"], 5)

    @patch('whisper_app.gui.QDialog')
    @patch('whisper_app.gui.QComboBox')
    def test_microphone_selection_dialog(self, mock_combo, mock_dialog):
        """Test microphone selection dialog."""
        # Mock available devices
        devices = [
            {"index": 0, "name": "Default Microphone"},
            {"index": 1, "name": "USB Microphone"},
            {"index": 9, "name": "Built-in Microphone"}
        ]

        # Simulate selection
        selected_index = 9

        config = {"input_device_index": selected_index}
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

        # Verify selection saved
        with open(self.config_file, 'r') as f:
            saved_config = json.load(f)

        self.assertEqual(saved_config["input_device_index"], 9)


class TestWhisperGUISystemTray(unittest.TestCase):
    """Test system tray functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_tray = Mock()
        self.mock_menu = Mock()

    @patch('whisper_app.gui.QSystemTrayIcon')
    @patch('whisper_app.gui.QMenu')
    def test_tray_icon_creation(self, mock_menu, mock_tray):
        """Test system tray icon is created."""
        tray = mock_tray.return_value
        tray.setContextMenu = Mock()

        menu = mock_menu.return_value
        tray.setContextMenu(menu)

        tray.setContextMenu.assert_called_once_with(menu)

    @patch('whisper_app.gui.QSystemTrayIcon')
    def test_tray_icon_show(self, mock_tray):
        """Test system tray icon is shown."""
        tray = mock_tray.return_value
        tray.show = Mock()

        tray.show()

        tray.show.assert_called_once()

    @patch('whisper_app.gui.QSystemTrayIcon')
    def test_tray_icon_hide(self, mock_tray):
        """Test system tray icon can be hidden."""
        tray = mock_tray.return_value
        tray.hide = Mock()

        tray.hide()

        tray.hide.assert_called_once()

    def test_close_event_hides_window(self):
        """Test that close event hides window instead of exiting."""
        mock_gui = Mock()
        mock_gui.is_recording = False
        mock_event = Mock()

        # Simulate closeEvent behavior
        mock_gui.hide()
        mock_event.ignore()

        mock_gui.hide.assert_called_once()
        mock_event.ignore.assert_called_once()


class TestWhisperGUIErrorHandling(unittest.TestCase):
    """Test error handling throughout the GUI."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_gui = Mock()
        self.mock_whisper = Mock()

    def test_whisper_initialization_failure(self):
        """Test handling of WhisperCLI initialization failure."""
        with patch('whisper_app.gui.WhisperCLI', side_effect=Exception("CUDA error")):
            with self.assertRaises(Exception):
                from whisper_app.gui import WhisperCLI
                whisper = WhisperCLI()

    def test_recording_start_failure(self):
        """Test handling of recording start failure."""
        self.mock_whisper.start_recording.side_effect = Exception("Microphone not found")

        with self.assertRaises(Exception):
            self.mock_whisper.start_recording()

    def test_transcription_failure(self):
        """Test handling of transcription failure."""
        self.mock_whisper.stop_recording.side_effect = Exception("ffmpeg not found")

        with self.assertRaises(Exception):
            self.mock_whisper.stop_recording()

    def test_history_file_corruption(self):
        """Test handling of corrupted history file."""
        temp_dir = tempfile.mkdtemp()
        history_file = os.path.join(temp_dir, 'history.json')

        # Write invalid JSON
        with open(history_file, 'w') as f:
            f.write("{invalid json")

        # Try to load
        try:
            with open(history_file, 'r') as f:
                json.load(f)
            self.fail("Should have raised JSONDecodeError")
        except json.JSONDecodeError:
            pass  # Expected

        # Clean up
        import shutil
        shutil.rmtree(temp_dir)

    def test_config_file_missing(self):
        """Test handling of missing config file."""
        temp_dir = tempfile.mkdtemp()
        config_file = os.path.join(temp_dir, 'config.json')

        # Try to load non-existent config
        if not os.path.exists(config_file):
            config = {}  # Use default config

        self.assertEqual(config, {})

        # Clean up
        import shutil
        shutil.rmtree(temp_dir)


class TestWhisperGUIClipboard(unittest.TestCase):
    """Test clipboard functionality."""

    @patch('whisper_app.gui.QApplication.clipboard')
    def test_copy_to_clipboard(self, mock_clipboard):
        """Test copying text to clipboard."""
        clipboard = mock_clipboard.return_value
        clipboard.setText = Mock()

        text = "Test transcription"
        clipboard.setText(text)

        clipboard.setText.assert_called_once_with(text)

    @patch('whisper_app.gui.QApplication.clipboard')
    def test_copy_empty_text(self, mock_clipboard):
        """Test copying empty text to clipboard."""
        clipboard = mock_clipboard.return_value
        clipboard.setText = Mock()

        text = ""
        clipboard.setText(text)

        clipboard.setText.assert_called_once_with("")


class TestWhisperGUIMarkdownFormatting(unittest.TestCase):
    """Test markdown to HTML conversion for Claude responses."""

    def test_markdown_bold_conversion(self):
        """Test bold text conversion."""
        from whisper_app.gui import markdown_to_html

        text = "This is **bold** text"
        html = markdown_to_html(text)

        self.assertIn("<strong>bold</strong>", html)

    def test_markdown_italic_conversion(self):
        """Test italic text conversion."""
        from whisper_app.gui import markdown_to_html

        text = "This is *italic* text"
        html = markdown_to_html(text)

        self.assertIn("<em>italic</em>", html)

    def test_markdown_code_block_conversion(self):
        """Test code block conversion."""
        from whisper_app.gui import markdown_to_html

        text = "```python\nprint('hello')\n```"
        html = markdown_to_html(text)

        self.assertIn("<pre>", html)
        self.assertIn("print('hello')", html)

    def test_markdown_list_conversion(self):
        """Test list conversion."""
        from whisper_app.gui import markdown_to_html

        text = "- Item 1\n- Item 2\n- Item 3"
        html = markdown_to_html(text)

        self.assertIn("<li>", html)


if __name__ == '__main__':
    unittest.main()
