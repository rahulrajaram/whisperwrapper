#!/usr/bin/env python3
"""
Alternative hotkey daemon using Wayland-compatible method
Uses D-Bus and systemd-logind for global input monitoring
"""

import sys
import os
import subprocess
import time
from pathlib import Path

try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
except ImportError:
    print("❌ Missing dependencies for Wayland mode")
    print("Install with: pip install dbus-python PyGObject")
    sys.exit(1)

class WaylandHotkeyDaemon:
    """Wayland-compatible hotkey daemon using D-Bus"""

    def __init__(self, debug=False):
        self.debug = debug
        self.recording = False
        self.whisper_process = None
        self.whisper_dir = Path(__file__).parent

    def _debug(self, msg):
        if self.debug:
            print(f"[WAYLAND] {msg}", file=sys.stderr)

    def _log(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def start_recording(self):
        """Start recording via whisper_hotkey_recorder"""
        if self.recording:
            return

        self.recording = True
        self._log("🎤 Starting voice recording...")

        try:
            recorder = self.whisper_dir / "whisper_hotkey_recorder.py"
            self.whisper_process = subprocess.Popen(
                [sys.executable, str(recorder)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as e:
            self._log(f"Error starting recording: {e}")
            self.recording = False

    def stop_recording(self):
        """Stop recording"""
        if not self.recording or not self.whisper_process:
            return

        self._log("⏹️  Stopping recording...")
        self.recording = False

        try:
            self.whisper_process.terminate()
            self.whisper_process.wait(timeout=5)
            self._log("✅ Recording saved to clipboard")
        except Exception as e:
            self._log(f"Error stopping: {e}")
            self.whisper_process.kill()

    def run(self):
        """Run the daemon using keyboard monitoring"""
        self._log("🚀 Wayland Hotkey Daemon starting...")
        self._log("Note: Using fallback hotkey detection for Wayland")
        self._log("")
        self._log("This method monitors keyboard input but may have limited compatibility")
        self._log("For best results, use a desktop environment with native hotkey support")
        self._log("")

        # Try to use evdev with keyboard grab
        try:
            from evdev import InputDevice, ecodes, list_devices
            import glob

            # Find keyboard
            devices = glob.glob("/dev/input/event*")
            keyboard_path = None

            for path in devices:
                try:
                    device = InputDevice(path)
                    caps = device.capabilities()
                    if ecodes.EV_KEY in caps:
                        keys = caps[ecodes.EV_KEY]
                        has_letters = any(
                            ecodes.KEY_A <= k <= ecodes.KEY_Z
                            for k in keys if isinstance(k, int)
                        )
                        if has_letters:
                            keyboard_path = path
                            self._log(f"Using: {device.name} ({path})")
                            break
                except:
                    pass

            if not keyboard_path:
                self._log("❌ No keyboard found!")
                return

            # Monitor keyboard
            self._log("Listening for CTRL+ALT+R...")
            self._log("Press Ctrl+C to exit\n")

            device = InputDevice(keyboard_path)
            pressed_keys = set()

            for event in device.read_loop():
                if event.type != ecodes.EV_KEY:
                    continue

                try:
                    key_name = ecodes.KEY.get(event.code)
                    if not key_name:
                        continue
                except:
                    continue

                if event.value == 1:  # Press
                    pressed_keys.add(key_name)
                    self._debug(f"Key pressed: {key_name}")

                    # Check for CTRL+ALT+R
                    if key_name == 'KEY_R':
                        has_ctrl = any(k in pressed_keys for k in ['KEY_LEFTCTRL', 'KEY_RIGHTCTRL'])
                        has_alt = any(k in pressed_keys for k in ['KEY_LEFTALT', 'KEY_RIGHTALT'])

                        if has_ctrl and has_alt:
                            self._log("🎯 CTRL+ALT+R detected!")
                            if self.recording:
                                self.stop_recording()
                            else:
                                self.start_recording()

                    # Check for ENTER/ESC to stop
                    elif key_name in ('KEY_ENTER', 'KEY_ESC'):
                        if self.recording:
                            self._log("Stop key pressed")
                            self.stop_recording()

                elif event.value == 0:  # Release
                    pressed_keys.discard(key_name)

        except KeyboardInterrupt:
            self._log("\n👋 Exiting...")
        except PermissionError:
            self._log("❌ Permission denied")
            self._log("Make sure you're in the 'input' group")
        except Exception as e:
            self._log(f"❌ Error: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Wayland Hotkey Daemon")
    parser.add_argument("--debug", action="store_true", help="Debug output")
    args = parser.parse_args()

    daemon = WaylandHotkeyDaemon(debug=args.debug)
    try:
        daemon.run()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
