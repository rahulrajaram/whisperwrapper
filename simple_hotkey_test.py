#!/usr/bin/env python3
"""
Simple hotkey test - mimics the daemon's core logic
Useful for debugging hotkey detection
"""

import sys
import glob
from evdev import InputDevice, ecodes

def main():
    print("🔍 Simple Hotkey Test")
    print("=" * 60)
    print()

    # Find keyboard
    print("Finding keyboard device...")
    devices = glob.glob("/dev/input/event*")
    keyboards = []

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
                    keyboards.append((device.name, path))
                    print(f"✅ Found: {device.name} ({path})")
        except:
            pass

    if not keyboards:
        print("❌ No keyboards found!")
        return

    # Use first keyboard
    keyboard_name, keyboard_path = keyboards[0]
    print(f"\nUsing: {keyboard_name}")
    print(f"Path: {keyboard_path}")
    print()

    # Open device
    try:
        device = InputDevice(keyboard_path)
    except PermissionError:
        print("❌ Permission denied!")
        print("   Make sure you're in the 'input' group")
        return
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Start listening
    print("Listening for CTRL+ALT+R (5 seconds)...")
    print()

    pressed_keys = set()
    import time
    start = time.time()

    try:
        for event in device.read_loop():
            # Timeout after 5 seconds
            if time.time() - start > 5:
                print("\n⏱️  Timeout - no CTRL+ALT+R detected in 5 seconds")
                print("\nMake sure you pressed CTRL+ALT+R during the test!")
                break

            if event.type != ecodes.EV_KEY:
                continue

            # Get key name
            try:
                key_name = ecodes.KEY.get(event.code, f"UNKNOWN({event.code})")
            except:
                key_name = f"KEY({event.code})"

            # Track key state
            if event.value == 1:  # Press
                pressed_keys.add(key_name)
                print(f"➕ {key_name:20s} | Held: {pressed_keys}")

                # Check for CTRL+ALT+R
                if key_name == 'KEY_R':
                    has_ctrl = any(k in pressed_keys for k in ['KEY_LEFTCTRL', 'KEY_RIGHTCTRL'])
                    has_alt = any(k in pressed_keys for k in ['KEY_LEFTALT', 'KEY_RIGHTALT'])

                    if has_ctrl and has_alt:
                        print()
                        print("🎯🎯🎯 CTRL+ALT+R DETECTED! 🎯🎯🎯")
                        print()
                        print("✅ SUCCESS! The hotkey detection works!")
                        print("   The daemon should be able to detect CTRL+ALT+R")
                        return

            elif event.value == 0:  # Release
                pressed_keys.discard(key_name)
                print(f"➖ {key_name:20s} | Held: {pressed_keys}")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
