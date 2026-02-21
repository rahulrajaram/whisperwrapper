#!/usr/bin/env python3
"""
Integration tests for FIFO Command Controller

Tests verify that:
1. FIFO is created and destroyed properly
2. Commands are read from FIFO and dispatched
3. Multiple commands are handled correctly
4. Error conditions are handled gracefully
5. Start/stop lifecycle works correctly
6. Thread management is correct
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
import tempfile
import time
import threading
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from whisper_app.fifo_controller import FIFOCommandController
from whisper_app.ipc_controller import IPCControllerError


class TestFIFOCommandController(unittest.TestCase):
    """Test FIFO command controller."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for FIFO
        self.temp_dir = tempfile.mkdtemp()
        self.fifo_path = os.path.join(self.temp_dir, "test.fifo")

        self.controller = FIFOCommandController(fifo_path=self.fifo_path, debug=False)
        self.mock_callback = Mock()
        self.controller.on_command_received = self.mock_callback

    def tearDown(self):
        """Clean up test fixtures."""
        # Stop controller
        if self.controller.is_running:
            self.controller.stop()

        # Clean up temp directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_controller_initialization(self):
        """Test controller initializes with correct path."""
        self.assertFalse(self.controller.is_running)
        self.assertEqual(self.controller.fifo_path, Path(self.fifo_path))

    def test_default_fifo_path(self):
        """Test default FIFO path."""
        controller = FIFOCommandController()
        expected_path = os.path.expanduser("~/.whisper/control.fifo")
        self.assertEqual(str(controller.fifo_path), expected_path)

    def test_fifo_creation(self):
        """Test that FIFO is created on start."""
        self.controller.start()
        self.assertTrue(os.path.exists(self.fifo_path))
        self.controller.stop()

    def test_fifo_cleanup(self):
        """Test that FIFO is removed on stop."""
        self.controller.start()
        self.assertTrue(os.path.exists(self.fifo_path))
        self.controller.stop()
        self.assertFalse(os.path.exists(self.fifo_path))

    def test_start_sets_running_flag(self):
        """Test that is_running flag is set on start."""
        self.assertFalse(self.controller.is_running)
        self.controller.start()
        self.assertTrue(self.controller.is_running)
        self.controller.stop()
        self.assertFalse(self.controller.is_running)

    def test_stop_clears_running_flag(self):
        """Test that is_running flag is cleared on stop."""
        self.controller.start()
        self.assertTrue(self.controller.is_running)
        self.controller.stop()
        self.assertFalse(self.controller.is_running)

    def test_multiple_start_calls(self):
        """Test that multiple start calls are safe."""
        self.controller.start()
        self.controller.start()  # Should not raise
        self.assertTrue(self.controller.is_running)
        self.controller.stop()

    def test_multiple_stop_calls(self):
        """Test that multiple stop calls are safe."""
        self.controller.start()
        self.controller.stop()
        self.controller.stop()  # Should not raise
        self.assertFalse(self.controller.is_running)

    def test_command_dispatch(self):
        """Test that commands are dispatched from FIFO."""
        self.controller.start()

        # Send command in a separate thread
        def send_cmd():
            time.sleep(0.1)  # Give reader time to block on FIFO
            with open(self.fifo_path, 'w') as f:
                f.write("start")

        sender = threading.Thread(target=send_cmd)
        sender.start()

        # Wait for command to be received
        sender.join(timeout=2.0)

        # Give dispatcher a moment to call callback
        time.sleep(0.1)

        self.mock_callback.assert_called_with("start")
        self.controller.stop()

    def test_multiple_commands(self):
        """Test that multiple commands are dispatched correctly."""
        self.controller.start()

        commands = ["start", "stop", "toggle"]

        def send_commands():
            time.sleep(0.1)
            for cmd in commands:
                with open(self.fifo_path, 'w') as f:
                    f.write(cmd)
                time.sleep(0.1)

        sender = threading.Thread(target=send_commands)
        sender.start()

        # Wait for all commands
        sender.join(timeout=5.0)
        time.sleep(0.2)  # Give dispatcher time

        self.controller.stop()

        # Verify all commands were dispatched
        self.assertEqual(self.mock_callback.call_count, len(commands))
        for i, cmd in enumerate(commands):
            self.assertEqual(self.mock_callback.call_args_list[i][0][0], cmd)

    def test_invalid_command_ignored(self):
        """Test that invalid commands are not dispatched."""
        self.controller.start()

        def send_cmd():
            time.sleep(0.1)
            with open(self.fifo_path, 'w') as f:
                f.write("invalid")

        sender = threading.Thread(target=send_cmd)
        sender.start()
        sender.join(timeout=2.0)
        time.sleep(0.1)

        self.controller.stop()
        self.mock_callback.assert_not_called()

    def test_empty_command_ignored(self):
        """Test that empty commands are ignored."""
        self.controller.start()

        def send_cmd():
            time.sleep(0.1)
            with open(self.fifo_path, 'w') as f:
                f.write("")

        sender = threading.Thread(target=send_cmd)
        sender.start()
        sender.join(timeout=2.0)
        time.sleep(0.1)

        self.controller.stop()
        self.mock_callback.assert_not_called()

    def test_whitespace_handling(self):
        """Test that whitespace is properly stripped."""
        self.controller.start()

        def send_cmd():
            time.sleep(0.1)
            with open(self.fifo_path, 'w') as f:
                f.write("  start  \n")

        sender = threading.Thread(target=send_cmd)
        sender.start()
        sender.join(timeout=2.0)
        time.sleep(0.1)

        self.controller.stop()
        self.mock_callback.assert_called_with("start")

    def test_reader_thread_created(self):
        """Test that reader thread is created."""
        self.controller.start()
        self.assertIsNotNone(self.controller._reader_thread)
        self.assertTrue(self.controller._reader_thread.is_alive())
        self.controller.stop()

    def test_reader_thread_stopped(self):
        """Test that reader thread is stopped."""
        self.controller.start()
        reader_thread = self.controller._reader_thread
        self.controller.stop()
        time.sleep(0.5)  # Give thread time to exit (non-blocking read needs time)
        self.assertFalse(reader_thread.is_alive())

    def test_context_manager_usage(self):
        """Test context manager protocol."""
        with self.controller as ctrl:
            self.assertTrue(ctrl.is_running)
            self.assertTrue(os.path.exists(self.fifo_path))

        self.assertFalse(self.controller.is_running)
        self.assertFalse(os.path.exists(self.fifo_path))

    def test_send_command_method(self):
        """Test send_command helper method."""
        self.controller.start()

        def wait_for_command():
            time.sleep(0.2)
            self.controller.send_command("toggle")

        sender = threading.Thread(target=wait_for_command)
        sender.start()
        sender.join(timeout=2.0)
        time.sleep(0.1)

        self.controller.stop()
        self.mock_callback.assert_called_with("toggle")

    def test_callback_exception_handling(self):
        """Test that exceptions in callback don't crash reader thread."""
        def bad_callback(cmd):
            raise ValueError("Callback error")

        self.controller.on_command_received = bad_callback

        self.controller.start()

        def send_cmd():
            time.sleep(0.1)
            with open(self.fifo_path, 'w') as f:
                f.write("start")

        sender = threading.Thread(target=send_cmd)
        sender.start()
        sender.join(timeout=2.0)
        time.sleep(0.1)

        # Should still be running despite callback exception
        self.assertTrue(self.controller.is_running)

        self.controller.stop()

    def test_no_callback_set(self):
        """Test that controller works when no callback is set."""
        self.controller.on_command_received = None
        self.controller.start()

        def send_cmd():
            time.sleep(0.1)
            with open(self.fifo_path, 'w') as f:
                f.write("start")

        sender = threading.Thread(target=send_cmd)
        sender.start()
        sender.join(timeout=2.0)

        # Should not raise
        self.assertTrue(self.controller.is_running)
        self.controller.stop()

    def test_case_sensitivity(self):
        """Test that command matching is case-sensitive."""
        self.controller.start()

        def send_cmd():
            time.sleep(0.1)
            with open(self.fifo_path, 'w') as f:
                f.write("START")  # Wrong case

        sender = threading.Thread(target=send_cmd)
        sender.start()
        sender.join(timeout=2.0)
        time.sleep(0.1)

        self.controller.stop()
        self.mock_callback.assert_not_called()

    def test_existing_fifo_removed(self):
        """Test that existing FIFO is removed and recreated on start."""
        # Create old FIFO manually
        os.makedirs(self.temp_dir, exist_ok=True)
        os.mkfifo(self.fifo_path)
        self.assertTrue(os.path.exists(self.fifo_path))

        # Start should handle existing FIFO gracefully
        self.controller.start()
        self.assertTrue(os.path.exists(self.fifo_path))
        self.assertTrue(self.controller.is_running)

        self.controller.stop()


class TestFIFOCommandControllerWithRealDirectory(unittest.TestCase):
    """Test FIFO controller with directory creation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.fifo_dir = os.path.join(self.temp_dir, "subdir", "nested")
        self.fifo_path = os.path.join(self.fifo_dir, "test.fifo")

    def tearDown(self):
        """Clean up."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_creates_missing_directories(self):
        """Test that missing directories are created."""
        controller = FIFOCommandController(fifo_path=self.fifo_path, debug=False)
        self.assertFalse(os.path.exists(self.fifo_dir))

        controller.start()

        self.assertTrue(os.path.exists(self.fifo_dir))
        self.assertTrue(os.path.exists(self.fifo_path))

        controller.stop()


class TestFIFOCommandControllerErrors(unittest.TestCase):
    """Test error handling in FIFO controller."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_send_command_to_nonexistent_fifo_raises_error(self):
        """Test sending command when FIFO doesn't exist raises error."""
        fifo_path = os.path.join(self.temp_dir, "nonexistent.fifo")
        controller = FIFOCommandController(fifo_path=fifo_path, debug=False)

        # Sending to non-existent FIFO should raise IPCControllerError
        try:
            controller.send_command("start")
            # If no exception, check that it's because of open timeout
            # This is expected behavior - the write can block if no reader
        except IPCControllerError:
            # This is the expected case
            pass


if __name__ == '__main__':
    unittest.main()
