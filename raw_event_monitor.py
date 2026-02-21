#!/usr/bin/env python3
"""
Raw event monitor - shows exactly what evdev sees
"""

import sys
import glob
from evdev import InputDevice, ecodes

def main():
    print("🔍 Raw Event Monitor")
    print("=" * 60)

    # Get device path from argument or auto-detect
    if len(sys.argv) > 1:
        device_path = sys.argv[1]
    else:
        # Find first keyboard
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
            except:
                pass

        if not keyboards:
            print("❌ No keyboards found!")
            return

        device_path = keyboards[0][1]
        print(f"Using: {keyboards[0][0]} ({device_path})")

    print("\nListening for events...")
    print("(Press CTRL+C to exit)\n")

    try:
        device = InputDevice(device_path)

        for event in device.read_loop():
            if event.type == ecodes.EV_KEY:
                try:
                    key_name = ecodes.KEY[event.code]
                except:
                    key_name = f"KEY_{event.code}"

                state = "DOWN" if event.value == 1 else "UP  "
                print(f"[{state}] code={event.code:3d} name={key_name:25s}")

            elif event.type == ecodes.EV_SYN:
                print(f"[SYN]  code={event.code:3d}")

    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
