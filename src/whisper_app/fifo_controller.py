#!/usr/bin/env python3
"""
FIFO-based IPC Controller Implementation

Uses named pipes (FIFOs) for inter-process communication.
This is the default IPC mechanism for the Whisper GUI.

Features:
- Simple and reliable file-based communication
- No external dependencies
- Works on any Unix-like system
- Easy to debug (can cat the FIFO directly)

Limitations:
- Local machine only (no network support)
- Requires file system access
- No authentication/encryption

IMPLEMENTATION NOTES (Hotkey Command Fix):

This module implements the CORRECT blocking FIFO pattern that prevents periodic hotkey
breakage. The key insight is understanding FIFO producer-consumer semantics:

WHAT FAILED (Nested loops with non-blocking reads):
- Used os.open() with O_NONBLOCK flag
- Tried to read multiple times from same file descriptor
- After 7-8 read cycles, FIFO state became corrupted
- Hotkey daemon would stop responding

WHY IT FAILED:
- Hotkey daemon: open(FIFO) -> write(command) -> close(FIFO)
- GUI with nested loops: try to read multiple times from same fd
- Multiple reads from same fd desynchronizes producer/consumer state
- FIFO assumes open-write-close per transaction, not multiple reads per fd

WHAT WORKS (Blocking open with single read per cycle):
- Reader thread calls open(FIFO) and BLOCKS until daemon opens as writer
- When daemon opens as writer, reader's open() returns
- Reader reads ONE message
- Reader closes fd and loops back to open()
- Loop repeats: reader waits for next daemon connection

WHY THIS WORKS:
- Standard FIFO pattern (one read per open-close cycle)
- Natural synchronization via blocking semantics
- No state corruption possible
- Matches daemon's request-response pattern exactly

SHUTDOWN MECHANISM:
- When GUI stops: stop() method opens FIFO as writer
- This unblocks reader's open() call
- Reader checks _stop_event and exits cleanly
- This is documented in the stop() method

See stop() and _read_loop() docstrings for detailed comments on the implementation.
"""

import os
import threading
import time
import logging
from pathlib import Path
from typing import Optional

from .ipc_controller import CommandController, IPCControllerError


logger = logging.getLogger(__name__)


class FIFOCommandController(CommandController):
    """FIFO-based command controller.

    Uses a named pipe (FIFO) at ~/.whisper/control.fifo for communication.
    A background thread listens for commands and dispatches them.

    Usage:
        controller = FIFOCommandController()
        controller.on_command_received = handle_command
        controller.start()
        # ... commands are received and dispatched ...
        controller.stop()
    """

    def __init__(self, fifo_path: Optional[str] = None, debug: bool = False):
        """Initialize FIFO controller.

        Args:
            fifo_path: Path to FIFO file. Defaults to ~/.whisper/control.fifo
            debug: Enable debug logging
        """
        super().__init__(debug=debug)

        if fifo_path is None:
            fifo_path = os.path.expanduser("~/.whisper/control.fifo")

        self.fifo_path = Path(fifo_path)
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start listening for commands on the FIFO.

        Creates the FIFO if it doesn't exist, then starts a background thread
        to read commands from it.

        Raises:
            IPCControllerError: If FIFO creation or thread start fails
        """
        if self._running:
            if self.debug:
                logger.debug("FIFO controller already running")
            return

        try:
            # Create FIFO directory if needed
            self.fifo_path.parent.mkdir(parents=True, exist_ok=True)

            # Remove old FIFO if it exists
            if self.fifo_path.exists():
                try:
                    self.fifo_path.unlink()
                    if self.debug:
                        logger.debug(f"Removed old FIFO: {self.fifo_path}")
                except OSError as e:
                    logger.warning(f"Could not remove old FIFO: {e}")

            # Create new FIFO
            try:
                os.mkfifo(str(self.fifo_path))
                if self.debug:
                    logger.debug(f"✅ Created FIFO at {self.fifo_path}")
            except FileExistsError:
                # FIFO already exists, which is okay
                if self.debug:
                    logger.debug(f"FIFO already exists: {self.fifo_path}")

            # Start reader thread
            self._stop_event.clear()
            self._reader_thread = threading.Thread(
                target=self._read_loop,
                daemon=True,
                name="FIFOReader"
            )
            self._reader_thread.start()
            self._running = True

            if self.debug:
                logger.debug(f"📡 FIFO command controller started (listening on {self.fifo_path})")

        except Exception as e:
            error_msg = f"Failed to start FIFO controller: {e}"
            logger.error(error_msg)
            raise IPCControllerError(error_msg) from e

    def stop(self) -> None:
        """Stop listening for commands.

        Signals the reader thread to stop and waits for it to finish.
        To interrupt a thread blocked in open(), we open the FIFO as a writer.

        CRITICAL FIX (Issue: Periodic hotkey breakage after 7-8 commands):
        - The reader thread's _read_loop() uses blocking open() semantics
        - It waits indefinitely for the hotkey daemon to connect as a writer
        - Simply setting _stop_event doesn't interrupt the blocked open() call
        - Solution: We open the FIFO as a writer to unblock the reader's open()
        - This allows the reader thread to check _stop_event and exit gracefully

        Root cause of previous failures:
        - Nested while loops with non-blocking reads corrupted FIFO state
        - After 7-8 reads, the FIFO would become unresponsive
        - Switching to blocking open() (standard FIFO pattern) fixed the corruption
        - But blocking open() requires explicit interrupt mechanism (this method)
        """
        if not self._running:
            if self.debug:
                logger.debug("FIFO controller not running")
            return

        try:
            if self.debug:
                logger.debug("Stopping FIFO controller...")

            # Signal thread to stop
            self._stop_event.set()

            # CRITICAL INTERRUPT: Open FIFO as writer to unblock reader's open() call
            # This is the key to graceful shutdown with blocking semantics
            # When reader's open() call returns (because we opened as writer),
            # it will check _stop_event.is_set() and exit the read loop
            if self.fifo_path.exists():
                try:
                    # Use O_NONBLOCK to avoid hanging if there's no reader
                    # We're just trying to wake up the blocking open() call
                    fd = os.open(str(self.fifo_path), os.O_WRONLY | os.O_NONBLOCK)
                    try:
                        os.close(fd)
                    except OSError:
                        pass
                    if self.debug:
                        logger.debug("Opened FIFO as writer to interrupt reader")
                except (OSError, FileNotFoundError):
                    # FIFO might not exist, or might have no reader - that's OK
                    # This is expected in tests where reader may have already exited
                    pass

            # Wait for thread to finish (with timeout)
            if self._reader_thread and self._reader_thread.is_alive():
                self._reader_thread.join(timeout=2.0)
                if self._reader_thread.is_alive():
                    logger.warning("Reader thread did not stop within timeout")

            # Clean up FIFO
            if self.fifo_path.exists():
                try:
                    self.fifo_path.unlink()
                    if self.debug:
                        logger.debug(f"Removed FIFO: {self.fifo_path}")
                except OSError as e:
                    logger.warning(f"Could not remove FIFO: {e}")

            self._running = False
            if self.debug:
                logger.debug("FIFO controller stopped")

        except Exception as e:
            logger.error(f"Error stopping FIFO controller: {e}")
            self._running = False

    def _read_loop(self) -> None:
        """Main loop for reading commands from FIFO.

        This runs in a background thread and reads commands from the FIFO.
        Uses blocking semantics: blocks on open until hotkey daemon connects, reads one message, closes, repeats.
        This is the standard FIFO pattern and most reliable for the production hotkey daemon use case.

        DESIGN RATIONALE (Fixed Periodic Hotkey Breakage):

        Previous implementation used nested loops with non-blocking os.open():
          while not stop_event.is_set():                    # Outer loop
              fd = os.open(path, O_NONBLOCK)
              while not stop_event.is_set():                # Inner loop - PROBLEM
                  try_read()                                # Multiple reads from same fd

        This caused FIFO state corruption after 7-8 reads because:
        - Hotkey daemon opens FIFO, writes 1 command, closes
        - Inner loop tries to read again from same fd = empty read
        - This desynchronizes daemon and reader state

        Current implementation uses simple blocking semantics:
          while not stop_event.is_set():
              open(path)                    # Blocks until daemon connects
              read_once()                   # Single read per connection
              close()                       # Close immediately
              loop back                     # Wait for next daemon connection

        Why this works:
        - Standard FIFO pattern (open, read, close pattern)
        - One read per fd lifecycle = no state corruption
        - Hotkey daemon expects simple request-response pattern
        - Blocking open() provides natural synchronization

        Shutdown mechanism:
        - Thread's stop() method opens FIFO as writer (see stop() docstring)
        - This unblocks the reader's open() call
        - Reader then checks _stop_event.is_set() and exits gracefully
        """
        try:
            while not self._stop_event.is_set():
                try:
                    # BLOCKING OPEN: Standard FIFO pattern
                    # Waits indefinitely until hotkey daemon opens as writer
                    # This is how FIFOs are designed to work (producer-consumer sync)
                    # When daemon connects, open() returns and we can read the command
                    with open(str(self.fifo_path), 'r') as fifo:
                        # Read the complete message from daemon
                        # fifo.read() blocks until daemon closes the FIFO
                        # (daemon opens, writes, closes = we get the data)
                        data = fifo.read().strip()

                        # Only dispatch if there's actual data
                        # Empty reads shouldn't happen with proper FIFO semantics
                        if data:
                            if self.debug:
                                logger.debug(f"🔔 Received command: {data}")
                            self._dispatch_command(data)

                    # Loop back to open() and wait for next daemon connection
                    # This avoids any nested-loop corruption

                except FileNotFoundError:
                    # FIFO was removed (expected during shutdown when stop() deletes it)
                    if self._stop_event.is_set():
                        break  # Normal shutdown exit
                    # If not stopping but FIFO missing, wait and retry
                    # (shouldn't happen in normal operation)
                    logger.debug("FIFO not found, waiting for restart...")
                    time.sleep(0.1)

                except OSError as e:
                    # Various OS errors (broken pipe, I/O error, etc.)
                    if self._stop_event.is_set():
                        break  # Expected error during shutdown
                    # Otherwise log and retry
                    logger.debug(f"FIFO read error: {e}")
                    time.sleep(0.1)  # Prevent tight loop on error

                except Exception as e:
                    # Unexpected errors (shouldn't reach here)
                    logger.error(f"Unexpected error in FIFO read loop: {e}", exc_info=True)
                    time.sleep(0.1)

        except Exception as e:
            logger.error(f"Fatal error in FIFO reader thread: {e}", exc_info=True)
        finally:
            if self.debug:
                logger.debug("FIFO reader thread exiting")

    def send_command(self, command: str) -> None:
        """Send a command through the FIFO (for testing).

        This method mirrors what the hotkey daemon does:
        1. Opens FIFO as writer (blocks until reader has open)
        2. Writes command
        3. Closes FIFO

        When reader's open() is waiting for a writer (blocking semantics),
        this open() call unblocks the reader and allows it to read the command.

        Args:
            command: Command to send ("start", "stop", or "toggle")

        Raises:
            IPCControllerError: If FIFO write fails
        """
        try:
            # Open as writer - this unblocks reader waiting in open()
            # Reader's open() returns when we open it as writer
            with open(str(self.fifo_path), 'w') as fifo:
                fifo.write(command)
                fifo.flush()  # Ensure command is sent immediately
            if self.debug:
                logger.debug(f"📤 Sent command: {command}")
        except Exception as e:
            error_msg = f"Failed to send command via FIFO: {e}"
            logger.error(error_msg)
            raise IPCControllerError(error_msg) from e


__all__ = ['FIFOCommandController']
