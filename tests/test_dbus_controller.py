#!/usr/bin/env python3
"""
Tests for D-Bus Command Controller

Tests the D-Bus implementation of the CommandController interface.
D-Bus tests focus on fallback and error handling since D-Bus might not be
available in all test environments.

Key Test Categories:
1. Graceful Fallback to FIFO
2. Error Handling
3. Lifecycle Management
4. Callback Registration
5. Configuration Options
"""

import unittest
import logging
import sys
from unittest.mock import Mock, patch, MagicMock
import tempfile

# Pre-mock heavy dependencies
sys.modules['torch'] = MagicMock()
sys.modules['whisper'] = MagicMock()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestDBusControllerFallback(unittest.TestCase):
    """Test D-Bus controller fallback behavior."""

    def test_initialization_without_dbus(self):
        """Test that controller initializes even without D-Bus."""
        from src.whisper_app.dbus_controller import DBusCommandController

        # Create controller with fallback enabled
        controller = DBusCommandController(use_fallback=True, debug=False)
        self.assertFalse(controller.is_running)
        self.assertIsNone(controller._fallback_controller)

    def test_fallback_to_fifo_when_start_fails(self):
        """Test that FIFO fallback is used on failure."""
        from src.whisper_app.dbus_controller import DBusCommandController

        with tempfile.TemporaryDirectory() as tmpdir:
            controller = DBusCommandController(use_fallback=True, debug=False)

            # Start should use FIFO fallback (D-Bus not available)
            controller.start()

            # Should be running with fallback controller
            self.assertTrue(controller.is_running)
            self.assertIsNotNone(controller._fallback_controller)

            # Stop should work
            controller.stop()
            self.assertFalse(controller.is_running)

    def test_error_when_fallback_disabled(self):
        """Test error raised when D-Bus unavailable and fallback disabled."""
        from src.whisper_app.dbus_controller import DBusCommandController
        from src.whisper_app.ipc_controller import IPCControllerError

        controller = DBusCommandController(use_fallback=False, debug=False)

        # Should raise error since D-Bus not available and fallback disabled
        with self.assertRaises(IPCControllerError):
            controller.start()

        self.assertFalse(controller.is_running)

    def test_callback_registration(self):
        """Test callback can be registered."""
        from src.whisper_app.dbus_controller import DBusCommandController

        controller = DBusCommandController(use_fallback=True)

        callback = Mock()
        controller.on_command_received = callback

        self.assertIs(controller.on_command_received, callback)

    def test_stop_when_not_running(self):
        """Test that stop is safe when not running."""
        from src.whisper_app.dbus_controller import DBusCommandController

        controller = DBusCommandController(use_fallback=True)

        # Stop without start should be safe
        controller.stop()
        self.assertFalse(controller.is_running)

    def test_multiple_start_stop_cycles(self):
        """Test multiple start/stop cycles."""
        from src.whisper_app.dbus_controller import DBusCommandController

        controller = DBusCommandController(use_fallback=True, debug=False)

        # First cycle
        controller.start()
        self.assertTrue(controller.is_running)
        controller.stop()
        self.assertFalse(controller.is_running)

        # Second cycle
        controller.start()
        self.assertTrue(controller.is_running)
        controller.stop()
        self.assertFalse(controller.is_running)

    def test_context_manager_protocol(self):
        """Test context manager support."""
        from src.whisper_app.dbus_controller import DBusCommandController

        controller = DBusCommandController(use_fallback=True, debug=False)

        with controller as ctx:
            self.assertTrue(ctx.is_running)
            self.assertIs(ctx, controller)

        self.assertFalse(controller.is_running)

    def test_context_manager_with_exception(self):
        """Test context manager cleans up on exception."""
        from src.whisper_app.dbus_controller import DBusCommandController

        controller = DBusCommandController(use_fallback=True, debug=False)

        try:
            with controller:
                self.assertTrue(controller.is_running)
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should still be cleaned up
        self.assertFalse(controller.is_running)

    def test_debug_mode(self):
        """Test debug mode setting."""
        controller1 = self._get_controller(debug=True)
        self.assertTrue(controller1.debug)

        controller2 = self._get_controller(debug=False)
        self.assertFalse(controller2.debug)

    def _get_controller(self, debug=False):
        """Helper to get a controller."""
        from src.whisper_app.dbus_controller import DBusCommandController
        return DBusCommandController(use_fallback=True, debug=debug)

    def test_service_constants(self):
        """Test that D-Bus service constants are defined."""
        from src.whisper_app.dbus_controller import DBusCommandController

        self.assertEqual(
            DBusCommandController.DBUS_SERVICE,
            "org.whisper.CommandControl"
        )
        self.assertEqual(
            DBusCommandController.DBUS_PATH,
            "/org/whisper/CommandControl"
        )
        self.assertEqual(
            DBusCommandController.DBUS_INTERFACE,
            "org.whisper.CommandControl"
        )

    def test_callback_with_fallback(self):
        """Test that callback is called through fallback controller."""
        from src.whisper_app.dbus_controller import DBusCommandController

        with tempfile.TemporaryDirectory() as tmpdir:
            controller = DBusCommandController(use_fallback=True, debug=False)

            # Register callback
            callback = Mock()
            controller.on_command_received = callback

            # Start (will use FIFO fallback)
            controller.start()

            # Verify fallback controller has the callback
            if controller._fallback_controller:
                self.assertEqual(
                    controller._fallback_controller.on_command_received,
                    callback
                )

            controller.stop()

    def test_is_running_property(self):
        """Test is_running property."""
        from src.whisper_app.dbus_controller import DBusCommandController

        controller = DBusCommandController(use_fallback=True, debug=False)

        self.assertFalse(controller.is_running)

        controller.start()
        self.assertTrue(controller.is_running)

        controller.stop()
        self.assertFalse(controller.is_running)

    def test_fallback_controller_not_created_if_unused(self):
        """Test that fallback controller isn't created until needed."""
        from src.whisper_app.dbus_controller import DBusCommandController

        controller = DBusCommandController(use_fallback=True, debug=False)

        # Before start, fallback should not be created
        self.assertIsNone(controller._fallback_controller)

        # After start, it should be created (since D-Bus not available)
        controller.start()
        self.assertIsNotNone(controller._fallback_controller)

        controller.stop()

    def test_multiple_stop_calls_safe(self):
        """Test that multiple stop calls are safe."""
        from src.whisper_app.dbus_controller import DBusCommandController

        controller = DBusCommandController(use_fallback=True, debug=False)

        controller.start()
        controller.stop()

        # Multiple stops should be safe
        controller.stop()
        controller.stop()

        self.assertFalse(controller.is_running)

    def test_inheritance_from_command_controller(self):
        """Test that DBusCommandController inherits from CommandController."""
        from src.whisper_app.dbus_controller import DBusCommandController
        from src.whisper_app.ipc_controller import CommandController

        self.assertTrue(issubclass(DBusCommandController, CommandController))

        controller = DBusCommandController(use_fallback=True)
        self.assertIsInstance(controller, CommandController)

    def test_has_required_methods(self):
        """Test that controller has all required CommandController methods."""
        from src.whisper_app.dbus_controller import DBusCommandController

        controller = DBusCommandController(use_fallback=True)

        # Check required methods exist
        self.assertTrue(hasattr(controller, 'start'))
        self.assertTrue(hasattr(controller, 'stop'))
        self.assertTrue(hasattr(controller, 'is_running'))
        self.assertTrue(hasattr(controller, 'on_command_received'))

        # Check they're callable
        self.assertTrue(callable(controller.start))
        self.assertTrue(callable(controller.stop))


if __name__ == '__main__':
    unittest.main()
