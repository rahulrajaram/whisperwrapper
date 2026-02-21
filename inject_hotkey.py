#!/usr/bin/env python3
"""
Inject hotkey events for testing the daemon
Simulates CTRL+ALT+R and RETURN key presses
"""

import sys
import time
from pathlib import Path

try:
    from evdev import UInput, ecodes
except ImportError:
    print("❌ Error: python3-evdev is not installed", file=sys.stderr)
    sys.exit(1)


def inject_hotkey(key_code, modifiers=[]):
    """Inject a key press with modifiers"""
    print(f"📤 Injecting: {' + '.join([m.__name__ if hasattr(m, '__name__') else str(m) for m in modifiers] + [f'KEY_{key_code}'])}")

    try:
        # Create a virtual input device
        ui = UInput()

        # Press modifiers
        for mod in modifiers:
            ui.write(ecodes.EV_KEY, mod, 1)
            time.sleep(0.05)

        # Press the main key
        ui.write(ecodes.EV_KEY, key_code, 1)
        ui.syn()
        time.sleep(0.1)

        # Release the main key
        ui.write(ecodes.EV_KEY, key_code, 0)
        ui.syn()
        time.sleep(0.05)

        # Release modifiers
        for mod in reversed(modifiers):
            ui.write(ecodes.EV_KEY, mod, 0)
            time.sleep(0.05)

        ui.syn()
        ui.close()

        print("✅ Event injected successfully!")
        return True

    except PermissionError:
        print("❌ Permission denied!")
        print("   You need to run this as root or with sudo")
        print("   Try: sudo ./inject_hotkey.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("🔧 Hotkey Event Injector")
    print("=" * 60)
    print()

    if len(sys.argv) > 1:
        if sys.argv[1] == "test-record":
            print("Testing: CTRL+ALT+R (Start Recording)")
            inject_hotkey(ecodes.KEY_R, [ecodes.KEY_LEFTCTRL, ecodes.KEY_LEFTALT])

        elif sys.argv[1] == "test-stop":
            print("Testing: RETURN (Stop Recording)")
            inject_hotkey(ecodes.KEY_RETURN, [])

        elif sys.argv[1] == "test-sequence":
            print("Testing: CTRL+ALT+R -> wait -> RETURN")
            print()
            print("1️⃣  Pressing CTRL+ALT+R...")
            inject_hotkey(ecodes.KEY_R, [ecodes.KEY_LEFTCTRL, ecodes.KEY_LEFTALT])
            print()

            print("⏳ Waiting 2 seconds...")
            time.sleep(2)
            print()

            print("2️⃣  Pressing RETURN...")
            inject_hotkey(ecodes.KEY_RETURN, [])
            print()

            print("✅ Test sequence complete!")

    else:
        print("Usage:")
        print("  sudo ./inject_hotkey.py test-record   # Inject CTRL+ALT+R")
        print("  sudo ./inject_hotkey.py test-stop     # Inject RETURN")
        print("  sudo ./inject_hotkey.py test-sequence # Full test (record + stop)")
        print()
        print("NOTE: Requires root/sudo access to inject events")


if __name__ == "__main__":
    main()
