#!/usr/bin/env python3
"""
Global hotkey listener for Whisper voice recorder (Wayland/X11 compatible)

Usage:
    # Run as daemon
    ./whisper_hotkey_daemon.py

    # Run with debug output
    ./whisper_hotkey_daemon.py --debug

Requirements:
    - python3-evdev: sudo apt-get install python3-evdev
    - Proper permissions: user must be in 'input' group

Hotkeys:
    CTRL+ALT+R - Start/stop recording
    ENTER or ESC - Stop recording and save to clipboard
"""

import sys
import os
import argparse
import threading
import time
import subprocess
import glob
from pathlib import Path

# Try to import evdev, provide helpful error if missing
try:
    from evdev import InputDevice, categorize, ecodes, list_devices
except ImportError:
    print("❌ Error: python3-evdev is not installed", file=sys.stderr)
    print("   Install with: sudo apt-get install python3-evdev", file=sys.stderr)
    sys.exit(1)


class WhisperHotkeyDaemon:
    """Global hotkey listener for Whisper voice recorder"""

    def __init__(self, debug=False):
        self.debug = debug
        self.recording = False
        self.whisper_process = None
        self.keyboard_device = None
        self.should_exit = False
        self.whisper_dir = Path(__file__).parent
        self.pressed_keys = set()  # Track currently pressed keys

    def _debug(self, message):
        """Print debug message if debug flag is enabled"""
        if self.debug:
            print(f"DEBUG: {message}", file=sys.stderr)

    def _log(self, message, level="INFO"):
        """Log message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def find_keyboard_device(self):
        """Find the primary keyboard input device"""
        self._debug("Searching for keyboard device...")

        keyboard_candidates = []

        # Strategy 1: Try to open evdev devices directly
        try:
            devices = list_devices()
            # If list_devices() returns empty, scan /dev/input directly
            if not devices:
                self._debug("list_devices() returned empty, scanning /dev/input directly...")
                devices = glob.glob("/dev/input/event*")

            for path in devices:
                try:
                    device = InputDevice(path)
                    self._debug(f"Checking {path}: {device.name}")

                    # Skip if it's a virtual device (from our own recording)
                    if "virtual" in device.name.lower():
                        continue

                    # Try to read capabilities
                    try:
                        capabilities = device.capabilities()
                        if ecodes.EV_KEY not in capabilities:
                            continue

                        keys = capabilities[ecodes.EV_KEY]
                        key_codes = [k for k in keys if isinstance(k, int)]
                        has_letters = any(
                            ecodes.KEY_A <= k <= ecodes.KEY_Z for k in key_codes
                        )

                        if has_letters:
                            keyboard_candidates.append((device.name, path))
                            self._debug(f"Found keyboard: {device.name} ({path})")

                    except Exception as e:
                        self._debug(f"Error reading capabilities for {path}: {e}")

                except PermissionError:
                    self._debug(f"Permission denied for {path}")
                except Exception as e:
                    self._debug(f"Error opening {path}: {e}")

        except Exception as e:
            self._debug(f"Error listing devices: {e}")

        # Strategy 2: If no keyboards found via capabilities, try common paths
        if not keyboard_candidates:
            self._debug("No keyboards found via capability check, trying common paths...")
            common_paths = [
                "/dev/input/event0",
                "/dev/input/event1",
                "/dev/input/event2",
                "/dev/input/event3",
            ]

            for path in common_paths:
                try:
                    device = InputDevice(path)
                    if "keyboard" in device.name.lower() or "kbd" in device.name.lower():
                        keyboard_candidates.append((device.name, path))
                        self._debug(f"Found via common path: {device.name} ({path})")
                except Exception as e:
                    self._debug(f"Error checking {path}: {e}")

        # Strategy 3: If still nothing, use the first available event device
        if not keyboard_candidates:
            self._debug("No keyboard found via strategies, using first available device...")
            try:
                devices = list_devices()
                if devices:
                    path = devices[0]
                    device = InputDevice(path)
                    keyboard_candidates.append((device.name, path))
                    self._debug(f"Using first available: {device.name} ({path})")
                    self._log(
                        "⚠️  Using first available input device. Results may vary.",
                        "WARN",
                    )
            except Exception as e:
                self._debug(f"Error getting first device: {e}")

        if not keyboard_candidates:
            self._log("No input devices found at all!", "ERROR")
            self._log(
                "Make sure you're in the 'input' group: groups $USER",
                "ERROR",
            )
            self._log(
                "You may also need to log out and log back in for group changes",
                "ERROR",
            )
            return None

        # Prefer actual keyboard devices over receivers/mice
        # Sort by device name to prefer keyboards
        keyboard_candidates.sort(
            key=lambda x: (
                # Prefer devices with "keyboard" in the name
                0 if "keyboard" in x[0].lower() else 1,
                # Then prefer "asus" or "at" keyboards
                0 if any(k in x[0].lower() for k in ["asus", "at translated"]) else 1,
                # Finally prefer devices with lower event numbers
                int(x[1].split("event")[-1]) if "event" in x[1] else 999,
            )
        )

        selected_name, selected_path = keyboard_candidates[0]
        self._log(f"Using input device: {selected_name} ({selected_path})")

        # Show alternatives if available
        if len(keyboard_candidates) > 1:
            self._debug(f"Available keyboard devices: {keyboard_candidates}")

        return selected_path

    def start_recording(self):
        """Start recording via whisper_hotkey_recorder"""
        if self.recording:
            self._debug("Already recording, ignoring start command")
            return

        self.recording = True
        self._log("🎤 Starting voice recording...")

        try:
            # Call the recorder helper which manages the recording session
            recorder_script = self.whisper_dir / "whisper_hotkey_recorder.py"
            if not recorder_script.exists():
                self._log(
                    f"Error: {recorder_script} not found!",
                    "ERROR",
                )
                self.recording = False
                return

            self.whisper_process = subprocess.Popen(
                [sys.executable, str(recorder_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self._debug(f"Started recording process (PID: {self.whisper_process.pid})")

        except Exception as e:
            self._log(f"Error starting recording: {e}", "ERROR")
            self.recording = False

    def stop_recording(self):
        """Stop recording and save to clipboard"""
        if not self.recording or not self.whisper_process:
            self._debug("No active recording to stop")
            return

        self._log("⏹️  Stopping recording and saving to clipboard...")
        self.recording = False

        try:
            # Send SIGTERM to gracefully stop the recording
            self.whisper_process.terminate()

            # Wait for process to finish (with timeout)
            try:
                stdout, stderr = self.whisper_process.communicate(timeout=5.0)
                if stdout:
                    self._debug(f"Recorder output: {stdout}")
                if stderr:
                    self._debug(f"Recorder error: {stderr}")
            except subprocess.TimeoutExpired:
                self._log("Recording process timeout, killing it", "WARN")
                self.whisper_process.kill()
                self.whisper_process.wait()

            self.whisper_process = None
            self._log("✅ Recording saved to clipboard")

        except Exception as e:
            self._log(f"Error stopping recording: {e}", "ERROR")
            self.recording = False

    def handle_key_event(self, device, event):
        """Handle a key press event"""
        try:
            # Only process EV_KEY events
            if event.type != ecodes.EV_KEY:
                return

            keycode = event.code
            keystate = event.value  # 0=release, 1=press, 2=hold

            # Get key name for tracking
            try:
                key_name = ecodes.KEY.get(keycode)
                if not key_name:
                    key_name = f"KEY({keycode})"
            except:
                key_name = f"KEY({keycode})"

            self._debug(f"[RAW] type={event.type}, code={keycode}, name={key_name}, value={keystate}")

            # Track pressed/released keys
            if keystate == 1:  # Press
                self.pressed_keys.add(key_name)
                self._debug(f"[KEY PRESS] {key_name} | Pressed: {self.pressed_keys}")

            elif keystate == 0:  # Release
                self.pressed_keys.discard(key_name)
                self._debug(f"[KEY RELEASE] {key_name} | Pressed: {self.pressed_keys}")

            # Check for CTRL+ALT+R (start/stop recording) on press
            if keycode == ecodes.KEY_R and keystate == 1:
                has_ctrl = any(k in self.pressed_keys for k in ['KEY_LEFTCTRL', 'KEY_RIGHTCTRL'])
                has_alt = any(k in self.pressed_keys for k in ['KEY_LEFTALT', 'KEY_RIGHTALT'])

                if has_ctrl and has_alt:
                    self._debug("🎯 CTRL+ALT+R detected!")
                    if self.recording:
                        self.stop_recording()
                    else:
                        self.start_recording()

            # Check for ENTER or ESC (stop recording) - only on initial press
            elif keystate == 1 and keycode in (ecodes.KEY_ENTER, ecodes.KEY_ESC):
                if self.recording:
                    self._debug(f"RETURN/ESC detected while recording")
                    self.stop_recording()

        except Exception as e:
            self._debug(f"Error handling key event: {e}")


    def listen_for_hotkeys(self):
        """Main loop to listen for hotkey events"""
        self._log("🎧 Listening for hotkeys (CTRL+ALT+R to start/stop recording)")
        self._log("Press Ctrl+C to exit")

        if not self.keyboard_device:
            self._log("No keyboard device available", "ERROR")
            return

        try:
            device = InputDevice(self.keyboard_device)
            self._log(f"Opened device: {device.name}")

            # Try to grab the device exclusively (requires sudo)
            try:
                device.grab()
                self._debug("Device grabbed exclusively")
            except Exception as e:
                self._debug(f"Could not grab device: {e} - will still listen to events")

            # Main event loop
            for event in device.read_loop():
                if self.should_exit:
                    break

                try:
                    self.handle_key_event(device, event)
                except Exception as e:
                    self._debug(f"Error in event loop: {e}")

        except PermissionError:
            self._log(
                "Permission denied! Make sure you're in the 'input' group:",
                "ERROR",
            )
            self._log("  sudo usermod -a -G input $USER", "ERROR")
            self._log("  Then log out and log back in", "ERROR")
            sys.exit(1)

        except FileNotFoundError:
            self._log(f"Device not found: {self.keyboard_device}", "ERROR")
            sys.exit(1)

        except Exception as e:
            self._log(f"Error during hotkey listening: {e}", "ERROR")
            sys.exit(1)

    def cleanup(self):
        """Clean up resources on exit"""
        self.should_exit = True

        if self.recording and self.whisper_process:
            self._log("Cleaning up: stopping recording...")
            self.stop_recording()

        self._log("👋 Exiting...")

    def run(self):
        """Start the hotkey daemon"""
        self._log("🚀 Whisper Hotkey Daemon starting...")

        # Find keyboard device
        self.keyboard_device = self.find_keyboard_device()
        if not self.keyboard_device:
            sys.exit(1)

        # Set up signal handlers
        import signal

        def signal_handler(sig, frame):
            self.cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start listening
        self.listen_for_hotkeys()


def main():
    parser = argparse.ArgumentParser(
        description="Global hotkey listener for Whisper voice recorder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run as daemon
  ./whisper_hotkey_daemon.py

  # Run with debug output
  ./whisper_hotkey_daemon.py --debug

Requirements:
  Install evdev: sudo apt-get install python3-evdev

  Set up permissions:
    sudo usermod -a -G input $USER
    (then log out and log back in)
        """,
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )

    args = parser.parse_args()

    daemon = WhisperHotkeyDaemon(debug=args.debug)

    try:
        daemon.run()
    except KeyboardInterrupt:
        daemon.cleanup()


if __name__ == "__main__":
    main()
