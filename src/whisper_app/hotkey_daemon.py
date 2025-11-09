#!/usr/bin/env python3
"""
Whisper Global Hotkey Daemon

Monitors for Ctrl+Alt+Shift+R hotkey to toggle recording in Whisper GUI.
Uses pynput to listen for keyboard events globally (works on X11 and Wayland).
Communicates with the GUI process via FIFO to send commands.
"""

import sys
import os
import signal
import logging
from pathlib import Path
from typing import Optional

from pynput import keyboard

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class WhisperHotkeyDaemon:
    """Global hotkey listener for Whisper GUI control."""

    # Define hotkey combination: Ctrl + Alt + Shift + R
    HOTKEY_MODIFIERS = {
        keyboard.Key.ctrl_l,
        keyboard.Key.alt_l,
        keyboard.Key.shift_l,
    }
    HOTKEY_KEY = 'r'

    def __init__(self, debug: bool = False):
        """Initialize the hotkey daemon.

        Args:
            debug: Enable debug logging
        """
        self.debug = debug
        if debug:
            logger.setLevel(logging.DEBUG)

        # Use the same FIFO path as the GUI's FIFO controller
        self.fifo_path = Path.home() / ".whisper" / "control.fifo"
        self.listener: Optional[keyboard.Listener] = None
        self.current_keys: set = set()
        self.running = True

        logger.info("Whisper Hotkey Daemon initialized")
        logger.info("Hotkey: Ctrl + Alt + Shift + R")
        logger.info(f"FIFO path: {self.fifo_path}")

    def send_command(self, command: str) -> bool:
        """Send a command to the GUI via FIFO.

        Args:
            command: Command to send ('toggle', 'start', or 'stop')

        Returns:
            True if successful, False otherwise
        """
        if not self.fifo_path.exists():
            logger.error(f"FIFO not found at {self.fifo_path}")
            logger.error("Make sure the Whisper GUI is running")
            return False

        try:
            with open(self.fifo_path, 'w') as fifo:
                fifo.write(command)
                fifo.flush()
            logger.debug(f"Sent command: {command}")
            return True
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            return False

    def on_press(self, key) -> None:
        """Handle key press events.

        Args:
            key: The key that was pressed
        """
        try:
            # Track modifier keys
            if key in self.HOTKEY_MODIFIERS:
                self.current_keys.add(key)
                logger.debug(f"Modifier keys pressed: {len(self.current_keys)}")

            # Check for the 'r' key
            if isinstance(key, keyboard.KeyCode) and key.char == self.HOTKEY_KEY:
                # Check if all modifiers are pressed
                if self.current_keys >= self.HOTKEY_MODIFIERS:
                    logger.info("Hotkey triggered: Ctrl+Alt+Shift+R")
                    self.send_command("toggle")
        except AttributeError:
            # Handle special keys that don't have the expected attributes
            pass

    def on_release(self, key) -> None:
        """Handle key release events.

        Args:
            key: The key that was released
        """
        try:
            if key in self.HOTKEY_MODIFIERS:
                self.current_keys.discard(key)
                logger.debug(f"Modifier keys pressed: {len(self.current_keys)}")
        except AttributeError:
            pass

    def signal_handler(self, sig, frame):
        """Handle shutdown signals.

        Args:
            sig: Signal number
            frame: Stack frame
        """
        logger.info(f"Received signal {sig}, shutting down...")
        self.running = False
        if self.listener:
            self.listener.stop()
        sys.exit(0)

    def run(self) -> None:
        """Start listening for hotkey events."""
        logger.info("Starting hotkey listener...")

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        try:
            # Create listener for keyboard events
            self.listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            )

            logger.info("Hotkey listener ready. Monitoring for Ctrl+Alt+Shift+R...")
            self.listener.start()

            # Keep the listener running
            self.listener.join()

        except Exception as e:
            logger.error(f"Error in hotkey listener: {e}")
            sys.exit(1)
        finally:
            if self.listener:
                self.listener.stop()
            logger.info("Hotkey daemon stopped")


def main():
    """Entry point for the hotkey daemon."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Whisper Global Hotkey Daemon"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    args = parser.parse_args()

    daemon = WhisperHotkeyDaemon(debug=args.debug)
    daemon.run()


if __name__ == "__main__":
    main()
