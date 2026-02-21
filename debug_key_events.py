#!/usr/bin/env python3
"""
Debug script to see actual key events being read
Shows exactly what the daemon is seeing
"""

import sys
from pathlib import Path
from evdev import InputDevice, categorize, ecodes

def monitor_keyboard():
    """Monitor and display all keyboard events"""
    device_path = "/dev/input/event0"  # AT Translated Set 2 keyboard

    try:
        device = InputDevice(device_path)
        print(f"Monitoring: {device.name}")
        print(f"Device: {device_path}")
        print()
        print("Press keys (CTRL+C to exit):")
        print("=" * 60)

        # Keep track of pressed keys
        pressed_keys = set()

        for event in device.read_loop():
            if event.type != ecodes.EV_KEY:
                continue

            key_name = ecodes.KEY.get(event.code, f"UNKNOWN({event.code})")
            state = "PRESSED" if event.value == 1 else "RELEASED"

            # Track pressed keys
            if event.value == 1:
                pressed_keys.add(key_name)
            else:
                pressed_keys.discard(key_name)

            print(f"{state:8s} | {key_name:20s} | Currently pressed: {pressed_keys}")

            # Check for CTRL+ALT+R
            if event.code == ecodes.KEY_R and event.value == 1:
                has_ctrl = (
                    'KEY_LEFTCTRL' in pressed_keys or 'KEY_RIGHTCTRL' in pressed_keys
                )
                has_alt = (
                    'KEY_LEFTALT' in pressed_keys or 'KEY_RIGHTALT' in pressed_keys
                )

                if has_ctrl and has_alt:
                    print()
                    print("🎯 CTRL+ALT+R DETECTED!")
                    print()

    except PermissionError:
        print("❌ Permission denied!")
        print("Make sure you're in the 'input' group")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Device not found: {device_path}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nExiting...")


if __name__ == "__main__":
    monitor_keyboard()
