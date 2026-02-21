#!/usr/bin/env python3
"""
D-Bus-based IPC Controller Implementation

Uses D-Bus (Desktop Bus) for inter-process communication.
D-Bus is the preferred IPC mechanism on modern Linux systems.

Features:
- Standard IPC mechanism on modern Linux desktops
- Well-established and secure
- Can be used both locally and over network
- Introspectable (tools can discover available services)
- Signal-based communication (efficient)

Limitations:
- Requires D-Bus session daemon running
- Requires dbus-python library
- More complex than FIFO but more robust

Fallback Behavior:
- If D-Bus is unavailable, attempts to use FIFO as fallback
- Allows graceful degradation on minimal systems
"""

import logging
import threading
from typing import Optional
from pathlib import Path

from .ipc_controller import CommandController, IPCControllerError

logger = logging.getLogger(__name__)

# Try to import dbus, but don't fail if not available
try:
    import dbus
    from dbus.service import Object, method
    from dbus.mainloop.glib import DBusGMainLoop
    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False
    logger.debug("dbus-python not available, D-Bus controller will use fallback")
    # Provide a dummy Object class for type safety when dbus is not available
    Object = object
    def method(*args, **kwargs):
        return lambda f: f


class DBusCommandController(CommandController):
    """D-Bus-based command controller.

    Registers a D-Bus service that listens for method calls and signals.
    If D-Bus is unavailable, falls back to FIFO implementation.

    Usage:
        controller = DBusCommandController()
        controller.on_command_received = handle_command
        controller.start()
        # ... commands are received and dispatched ...
        controller.stop()

    D-Bus Service Details:
        Service: org.whisper.CommandControl
        Path: /org/whisper/CommandControl
        Interface: org.whisper.CommandControl
        Methods: start, stop, toggle
    """

    # D-Bus service constants
    DBUS_SERVICE = "org.whisper.CommandControl"
    DBUS_PATH = "/org/whisper/CommandControl"
    DBUS_INTERFACE = "org.whisper.CommandControl"

    def __init__(self, use_fallback: bool = True, debug: bool = False):
        """Initialize D-Bus controller.

        Args:
            use_fallback: If True and D-Bus unavailable, use FIFO implementation
            debug: Enable debug logging
        """
        super().__init__(debug=debug)
        self.use_fallback = use_fallback
        self._fallback_controller: Optional[CommandController] = None
        self._dbus_object: Optional[Object] = None
        self._dbus_thread: Optional[threading.Thread] = None
        self._dbus_available = HAS_DBUS

        if not HAS_DBUS and debug:
            logger.debug("D-Bus not available, will use fallback if enabled")

    def start(self) -> None:
        """Start listening for D-Bus method calls.

        If D-Bus is available, registers the service on the session bus.
        If not available and fallback is enabled, uses FIFO implementation.

        Raises:
            IPCControllerError: If both D-Bus and fallback fail
        """
        if self._running:
            if self.debug:
                logger.debug("D-Bus controller already running")
            return

        try:
            if HAS_DBUS and self._try_dbus_start():
                return  # Successfully started with D-Bus

            # D-Bus failed or not available
            if self.use_fallback:
                if self.debug:
                    logger.debug("Falling back to FIFO implementation")
                self._use_fifo_fallback()
                return

            # No D-Bus and no fallback
            error_msg = "D-Bus not available and fallback disabled"
            logger.error(error_msg)
            raise IPCControllerError(error_msg)

        except Exception as e:
            error_msg = f"Failed to start D-Bus controller: {e}"
            logger.error(error_msg)
            raise IPCControllerError(error_msg) from e

    def _try_dbus_start(self) -> bool:  # pragma: no cover - requires D-Bus runtime
        """Try to start D-Bus service.

        Returns:
            True if successful, False if D-Bus unavailable
        """
        if not HAS_DBUS:
            return False

        try:
            # Get the session bus
            bus = dbus.SessionBus()

            # Request the service name
            try:
                # Use the proper flag constant
                flag = getattr(dbus.bus, 'NAME_FLAG_REPLACE_EXISTING', 1)
                bus.request_name(self.DBUS_SERVICE, flag)
            except (dbus.DBusException, AttributeError) as e:
                if self.debug:
                    logger.debug(f"Could not acquire D-Bus service name: {e}")
                return False

            # Create the D-Bus object
            self._dbus_object = _WhisperCommandObject(
                bus,
                self.DBUS_PATH,
                self.DBUS_INTERFACE,
                self._dispatch_command,
                debug=self.debug
            )

            self._running = True
            if self.debug:
                logger.debug(f"📡 D-Bus controller started (service: {self.DBUS_SERVICE})")

            return True

        except Exception as e:
            if self.debug:
                logger.debug(f"D-Bus initialization failed: {e}")
            return False

    def _use_fifo_fallback(self) -> None:  # pragma: no cover - exercised via integration
        """Use FIFO implementation as fallback."""
        if self._fallback_controller is None:
            # Import here to avoid circular dependencies
            from .fifo_controller import FIFOCommandController
            self._fallback_controller = FIFOCommandController(debug=self.debug)

        # Copy the callback
        self._fallback_controller.on_command_received = self.on_command_received

        # Start the fallback controller
        self._fallback_controller.start()
        self._running = True

        if self.debug:
            logger.debug("FIFO fallback controller started")

    def stop(self) -> None:
        """Stop listening for D-Bus method calls.

        Also stops any fallback controller if active.
        """
        if not self._running:
            if self.debug:
                logger.debug("D-Bus controller not running")
            return

        try:
            if self.debug:
                logger.debug("Stopping D-Bus controller...")

            # Stop fallback if active
            if self._fallback_controller is not None:
                self._fallback_controller.stop()
                self._fallback_controller = None

            # Clean up D-Bus object
            if self._dbus_object is not None:
                try:
                    self._dbus_object.remove_from_connection()
                except Exception as e:
                    logger.debug(f"Error removing D-Bus object: {e}")
                self._dbus_object = None

            self._running = False
            if self.debug:
                logger.debug("D-Bus controller stopped")

        except Exception as e:
            logger.error(f"Error stopping D-Bus controller: {e}")
            self._running = False

    def send_command(self, command: str) -> None:
        """Send a command via D-Bus (for testing).

        Args:
            command: Command to send ("start", "stop", or "toggle")

        Raises:
            IPCControllerError: If sending fails
        """
        if self._fallback_controller is not None:
            # Using FIFO fallback
            self._fallback_controller.send_command(command)
            return

        if not HAS_DBUS or self._dbus_object is None:
            raise IPCControllerError("D-Bus not available or not running")

        try:
            # Get the session bus and call the method on the object
            bus = dbus.SessionBus()
            remote_object = bus.get_object(self.DBUS_SERVICE, self.DBUS_PATH)
            interface = dbus.Interface(remote_object, self.DBUS_INTERFACE)

            # Call the appropriate method
            if command == "start":
                interface.Start()
            elif command == "stop":
                interface.Stop()
            elif command == "toggle":
                interface.Toggle()
            else:
                raise IPCControllerError(f"Unknown command: {command}")

            if self.debug:
                logger.debug(f"📤 Sent D-Bus command: {command}")

        except Exception as e:
            error_msg = f"Failed to send D-Bus command: {e}"
            logger.error(error_msg)
            raise IPCControllerError(error_msg) from e


class _WhisperCommandObject(Object):  # pragma: no cover - D-Bus object wrapper
    """D-Bus object that provides the Whisper command interface.

    This class is only instantiated if D-Bus is available.
    """

    def __init__(self, bus, path, interface, dispatch_callback, debug=False):
        """Initialize D-Bus object.

        Args:
            bus: D-Bus session bus
            path: D-Bus object path
            interface: D-Bus interface name
            dispatch_callback: Callback function for dispatching commands
            debug: Enable debug logging
        """
        Object.__init__(self, bus, path)
        self.dispatch_callback = dispatch_callback
        self.debug = debug
        self.interface = interface

    @method(DBusCommandController.DBUS_INTERFACE, in_signature='', out_signature='')
    def Start(self):
        """D-Bus method: Start recording."""
        if self.debug:
            logger.debug("D-Bus method called: Start")
        self.dispatch_callback("start")

    @method(DBusCommandController.DBUS_INTERFACE, in_signature='', out_signature='')
    def Stop(self):
        """D-Bus method: Stop recording."""
        if self.debug:
            logger.debug("D-Bus method called: Stop")
        self.dispatch_callback("stop")

    @method(DBusCommandController.DBUS_INTERFACE, in_signature='', out_signature='')
    def Toggle(self):
        """D-Bus method: Toggle recording."""
        if self.debug:
            logger.debug("D-Bus method called: Toggle")
        self.dispatch_callback("toggle")


__all__ = ['DBusCommandController']
