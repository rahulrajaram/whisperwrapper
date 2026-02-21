#!/usr/bin/env python3
"""
Debug script to monitor and log all keyboard input at the kernel level
Useful for figuring out the exact key names evdev detects
Works with Wayland and X11
"""

import sys
import glob
from datetime import datetime
from pathlib import Path

try:
    from evdev import InputDevice, list_devices, ecodes, categorize
except ImportError:
    print("❌ evdev is not installed!")
    print("Install with: pip install evdev")
    sys.exit(1)

# Setup logging file
log_file = Path.home() / ".whisper" / "hotkey_debug.log"
log_file.parent.mkdir(parents=True, exist_ok=True)

# Clear the log file at start
with open(log_file, 'w') as f:
    f.write(f"Hotkey Debug Log Started: {datetime.now()}\n")
    f.write("=" * 80 + "\n\n")

pressed_keys = set()

def log_message(msg):
    """Write message to both console and log file"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    log_entry = f"[{timestamp}] {msg}"
    print(log_entry)
    with open(log_file, 'a') as f:
        f.write(log_entry + "\n")

def find_keyboard_device():
    """Find the primary keyboard input device"""
    log_message("🔍 Searching for keyboard device...")

    keyboard_candidates = []

    # Try to find keyboard devices
    devices = list_devices() or glob.glob("/dev/input/event*")

    for path in devices:
        try:
            device = InputDevice(path)

            # Skip virtual devices
            if "virtual" in device.name.lower():
                continue

            # Check if device has keyboard capabilities
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
                    log_message(f"  Found keyboard: {device.name} ({path})")

            except Exception:
                continue

        except Exception:
            continue

    if keyboard_candidates:
        # Prefer USB keyboards, then any other keyboard
        for name, path in keyboard_candidates:
            if "usb" in name.lower():
                log_message(f"✅ Using USB keyboard: {name} ({path})")
                return InputDevice(path)

        # Fall back to first candidate
        name, path = keyboard_candidates[0]
        log_message(f"✅ Using keyboard: {name} ({path})")
        return InputDevice(path)

    log_message("❌ No keyboard device found")
    return None

def listen_for_keys(device):
    """Listen for keyboard events from device"""
    log_message("🎮 Listening for keyboard events...")
    log_message("Press keys now. Try CTRL+ALT+SHIFT+R")
    log_message("")

    try:
        for event in device.read_loop():
            # Only process key events
            if event.type != ecodes.EV_KEY:
                continue

            # Get the key code
            key_code = event.code
            key_name = ecodes.KEY[key_code] if key_code in ecodes.KEY else str(key_code)

            # Track key state
            if event.value == 1:  # Key pressed
                pressed_keys.add(key_name)
                log_message(f"KEY PRESSED:  {key_name}")
                log_message(f"  → Currently pressed: {pressed_keys}")

                # Check for hotkey combination
                has_ctrl = any(k in pressed_keys for k in ['KEY_LEFTCTRL', 'KEY_RIGHTCTRL'])
                has_alt = any(k in pressed_keys for k in ['KEY_LEFTALT', 'KEY_RIGHTALT'])
                has_shift = any(k in pressed_keys for k in ['KEY_LEFTSHIFT', 'KEY_RIGHTSHIFT'])
                has_r = 'KEY_R' in pressed_keys

                if has_ctrl and has_alt and has_shift and has_r:
                    log_message("🔴 HOTKEY DETECTED: CTRL+ALT+SHIFT+R ✓✓✓")

            elif event.value == 0:  # Key released
                pressed_keys.discard(key_name)
                log_message(f"KEY RELEASED: {key_name}")
                log_message(f"  → Currently pressed: {pressed_keys}")

    except KeyboardInterrupt:
        log_message("\n⏹️  Keyboard listener stopped by user")
    except Exception as e:
        log_message(f"❌ Error: {e}")
    finally:
        log_message("Exiting...")

if __name__ == "__main__":
    log_message("🚀 Starting evdev keyboard event logger...")
    log_message("📁 Log file: " + str(log_file))
    log_message("⚠️  This requires evdev which needs /dev/input access")
    log_message("   If you get permission errors, try:")
    log_message("   sudo usermod -a -G input $USER")
    log_message("   Then log out and log back in")
    log_message("")

    try:
        device = find_keyboard_device()
        if device:
            listen_for_keys(device)
        else:
            log_message("❌ Could not find keyboard device")
    except PermissionError:
        log_message("❌ Permission denied accessing /dev/input")
        log_message("   Add yourself to input group: sudo usermod -a -G input $USER")
    except Exception as e:
        log_message(f"❌ Error: {e}")
