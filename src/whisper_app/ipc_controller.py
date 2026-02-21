#!/usr/bin/env python3
"""
Abstract IPC Controller Interface

Defines the interface for external command control mechanisms.
Implementations can use FIFO, D-Bus, sockets, or other IPC mechanisms.

All commands are routed through callbacks to enable safe integration
with Qt's signal/slot mechanism.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable, Optional
import logging


logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Valid command types."""
    START = "start"
    STOP = "stop"
    TOGGLE = "toggle"


class IPCControllerError(Exception):
    """Base exception for IPC controller errors."""
    pass


class CommandController(ABC):
    """Abstract base class for external command control.

    Implementations provide different transport mechanisms (FIFO, D-Bus, sockets, etc.)
    but all follow the same interface. This allows the GUI to work with any transport
    without knowing implementation details.

    Commands are represented as strings: "start", "stop", "toggle"

    Usage:
        controller = FIFOCommandController()  # or DBusCommandController()
        controller.on_command_received = handle_command  # set callback
        controller.start()  # begin listening
        # ... commands will call on_command_received ...
        controller.stop()   # cleanup
    """

    def __init__(self, debug: bool = False):
        """Initialize command controller.

        Args:
            debug: Enable debug logging for this controller
        """
        self.debug = debug
        self._running = False
        self.on_command_received: Optional[Callable[[str], None]] = None

    @abstractmethod
    def start(self) -> None:
        """Start listening for commands.

        Raises:
            IPCControllerError: If controller fails to start
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop listening for commands.

        Should be safe to call even if not running.
        """
        pass

    @property
    def is_running(self) -> bool:
        """Check if controller is currently listening for commands."""
        return self._running

    def _validate_command(self, command: str) -> bool:
        """Validate that command is recognized.

        Args:
            command: Command string to validate

        Returns:
            True if valid, False otherwise
        """
        valid_commands = [cmd.value for cmd in CommandType]
        is_valid = command in valid_commands

        if self.debug:
            if is_valid:
                logger.debug(f"✓ Valid command: {command}")
            else:
                logger.warning(f"✗ Invalid command: {command} (expected one of: {valid_commands})")

        return is_valid

    def _dispatch_command(self, command: str) -> None:
        """Dispatch a command to the registered callback.

        Args:
            command: Command string to dispatch
        """
        if not self._validate_command(command):
            if self.debug:
                logger.warning(f"Ignoring invalid command: {command}")
            return

        if self.on_command_received is None:
            if self.debug:
                logger.warning("No command handler registered")
            return

        try:
            if self.debug:
                logger.debug(f"🔔 Dispatching command: {command}")
            self.on_command_received(command)
        except Exception as e:
            logger.error(f"Error dispatching command '{command}': {e}", exc_info=True)

    def __enter__(self):
        """Context manager support."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support."""
        self.stop()
        return False


__all__ = [
    'CommandController',
    'CommandType',
    'IPCControllerError',
]
