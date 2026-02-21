#!/usr/bin/env python3
"""
Unit tests for the abstract IPC Controller interface.

Tests verify that:
1. Abstract interface is properly defined
2. All implementations follow the interface contract
3. Command validation works correctly
4. Callbacks are properly dispatched
5. Error handling is robust
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from whisper_app.ipc_controller import (
    CommandController,
    CommandType,
    IPCControllerError,
)


class ConcreteCommandController(CommandController):
    """Concrete implementation for testing abstract interface."""

    def start(self) -> None:
        """Start listening."""
        self._running = True

    def stop(self) -> None:
        """Stop listening."""
        self._running = False


class TestCommandType(unittest.TestCase):
    """Test CommandType enum."""

    def test_valid_commands(self):
        """Test that all expected commands are defined."""
        self.assertEqual(CommandType.START.value, "start")
        self.assertEqual(CommandType.STOP.value, "stop")
        self.assertEqual(CommandType.TOGGLE.value, "toggle")

    def test_command_count(self):
        """Test that we have the expected number of commands."""
        commands = list(CommandType)
        self.assertEqual(len(commands), 3)


class TestCommandControllerInterface(unittest.TestCase):
    """Test the abstract CommandController interface."""

    def setUp(self):
        """Set up test fixtures."""
        self.controller = ConcreteCommandController(debug=True)
        self.mock_callback = Mock()

    def tearDown(self):
        """Clean up."""
        if self.controller.is_running:
            self.controller.stop()

    def test_controller_initialization(self):
        """Test that controller initializes properly."""
        self.assertIsNotNone(self.controller)
        self.assertFalse(self.controller.is_running)
        self.assertIsNone(self.controller.on_command_received)

    def test_start_stop_lifecycle(self):
        """Test start/stop lifecycle."""
        self.assertFalse(self.controller.is_running)
        self.controller.start()
        self.assertTrue(self.controller.is_running)
        self.controller.stop()
        self.assertFalse(self.controller.is_running)

    def test_multiple_start_calls(self):
        """Test that multiple start calls don't cause issues."""
        self.controller.start()
        self.controller.start()  # Should be idempotent
        self.assertTrue(self.controller.is_running)

    def test_multiple_stop_calls(self):
        """Test that multiple stop calls don't cause issues."""
        self.controller.start()
        self.controller.stop()
        self.controller.stop()  # Should be safe
        self.assertFalse(self.controller.is_running)

    def test_command_validation_valid(self):
        """Test validation of valid commands."""
        for cmd_type in CommandType:
            is_valid = self.controller._validate_command(cmd_type.value)
            self.assertTrue(is_valid, f"Command '{cmd_type.value}' should be valid")

    def test_command_validation_invalid(self):
        """Test validation of invalid commands."""
        invalid_commands = ["invalid", "help", "quit", "", "START", "Stop"]
        for cmd in invalid_commands:
            is_valid = self.controller._validate_command(cmd)
            self.assertFalse(is_valid, f"Command '{cmd}' should be invalid")

    def test_callback_registration(self):
        """Test that callbacks can be registered."""
        self.controller.on_command_received = self.mock_callback
        self.assertEqual(self.controller.on_command_received, self.mock_callback)

    def test_dispatch_command_with_callback(self):
        """Test that commands are dispatched to registered callback."""
        self.controller.on_command_received = self.mock_callback
        self.controller._dispatch_command("start")
        self.mock_callback.assert_called_once_with("start")

    def test_dispatch_all_valid_commands(self):
        """Test dispatching all valid command types."""
        self.controller.on_command_received = self.mock_callback
        for cmd_type in CommandType:
            self.mock_callback.reset_mock()
            self.controller._dispatch_command(cmd_type.value)
            self.mock_callback.assert_called_once_with(cmd_type.value)

    def test_dispatch_invalid_command_ignored(self):
        """Test that invalid commands are ignored (not dispatched)."""
        self.controller.on_command_received = self.mock_callback
        self.controller._dispatch_command("invalid")
        self.mock_callback.assert_not_called()

    def test_dispatch_without_callback(self):
        """Test that dispatch without callback doesn't crash."""
        self.controller.on_command_received = None
        # Should not raise
        self.controller._dispatch_command("start")

    def test_dispatch_callback_exception_handled(self):
        """Test that exceptions in callback are handled gracefully."""
        self.controller.on_command_received = Mock(side_effect=ValueError("Test error"))
        # Should not raise
        self.controller._dispatch_command("start")

    def test_context_manager_usage(self):
        """Test context manager protocol."""
        with self.controller as ctrl:
            self.assertTrue(ctrl.is_running)
        self.assertFalse(self.controller.is_running)

    def test_context_manager_with_exception(self):
        """Test context manager cleanup on exception."""
        try:
            with self.controller as ctrl:
                self.assertTrue(ctrl.is_running)
                raise ValueError("Test error")
        except ValueError:
            pass
        self.assertFalse(self.controller.is_running)

    def test_debug_flag(self):
        """Test debug flag initialization."""
        debug_controller = ConcreteCommandController(debug=True)
        self.assertTrue(debug_controller.debug)

        normal_controller = ConcreteCommandController(debug=False)
        self.assertFalse(normal_controller.debug)

    def test_command_callback_with_different_commands(self):
        """Test that different commands are correctly dispatched."""
        received_commands = []
        self.controller.on_command_received = lambda cmd: received_commands.append(cmd)

        self.controller._dispatch_command("start")
        self.controller._dispatch_command("stop")
        self.controller._dispatch_command("toggle")

        self.assertEqual(received_commands, ["start", "stop", "toggle"])

    def test_is_running_property_read_only(self):
        """Test that is_running property reflects actual state."""
        self.controller.start()
        self.assertTrue(self.controller.is_running)

        self.controller.stop()
        self.assertFalse(self.controller.is_running)

    def test_concurrent_commands(self):
        """Test that multiple commands can be dispatched in sequence."""
        call_count = 0

        def count_calls(cmd):
            nonlocal call_count
            call_count += 1

        self.controller.on_command_received = count_calls

        for i in range(10):
            self.controller._dispatch_command("start")

        self.assertEqual(call_count, 10)


class TestIPCControllerError(unittest.TestCase):
    """Test the IPCControllerError exception."""

    def test_error_creation(self):
        """Test creating an IPC controller error."""
        error = IPCControllerError("Test error message")
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Test error message")

    def test_error_inheritance(self):
        """Test that IPCControllerError inherits from Exception."""
        error = IPCControllerError("Test")
        self.assertIsInstance(error, Exception)


class TestCommandControllerIntegration(unittest.TestCase):
    """Integration tests for command controller."""

    def setUp(self):
        """Set up test fixtures."""
        self.controller = ConcreteCommandController(debug=False)
        self.received_commands = []

        def record_command(cmd):
            self.received_commands.append(cmd)

        self.controller.on_command_received = record_command

    def tearDown(self):
        """Clean up."""
        if self.controller.is_running:
            self.controller.stop()

    def test_full_lifecycle(self):
        """Test full lifecycle: init → start → commands → stop."""
        # Not running initially
        self.assertFalse(self.controller.is_running)

        # Start listening
        self.controller.start()
        self.assertTrue(self.controller.is_running)

        # Dispatch commands
        self.controller._dispatch_command("start")
        self.controller._dispatch_command("toggle")
        self.controller._dispatch_command("stop")

        # Verify all commands received
        self.assertEqual(self.received_commands, ["start", "toggle", "stop"])

        # Stop listening
        self.controller.stop()
        self.assertFalse(self.controller.is_running)

        # New commands ignored when not running... (implementation dependent)

    def test_command_sequence(self):
        """Test a realistic command sequence."""
        self.controller.start()

        # User presses hotkey to start recording
        self.controller._dispatch_command("start")
        # User presses hotkey to stop recording
        self.controller._dispatch_command("stop")
        # User presses hotkey to toggle (start recording)
        self.controller._dispatch_command("toggle")
        # User presses hotkey to toggle (stop recording)
        self.controller._dispatch_command("toggle")

        self.assertEqual(
            self.received_commands,
            ["start", "stop", "toggle", "toggle"]
        )

        self.controller.stop()


if __name__ == '__main__':
    unittest.main()
