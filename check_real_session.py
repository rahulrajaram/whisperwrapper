#!/usr/bin/env python3
"""
Check if we're in a real graphical session with keyboard access
"""

import os
import sys
import subprocess

print("🔍 Session Check")
print("=" * 70)
print()

# Check display variables
print("Display Variables:")
print(f"  DISPLAY={os.environ.get('DISPLAY', '(not set)')}")
print(f"  WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', '(not set)')}")
print(f"  XDG_VTNR={os.environ.get('XDG_VTNR', '(not set)')}")
print()

# Check if we have a graphical session
has_display = bool(os.environ.get('DISPLAY')) or bool(os.environ.get('WAYLAND_DISPLAY'))
print(f"Graphical Session: {'✅ YES' if has_display else '❌ NO'}")
print()

# Try to test keyboard access
print("Keyboard Access Test:")
print("=" * 70)

try:
    from evdev import InputDevice, list_devices, ecodes
    import glob

    devices = glob.glob("/dev/input/event*")
    print(f"Found {len(devices)} input devices")
    print()

    # Find keyboard
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
                    print(f"✅ Keyboard Found: {device.name}")
                    print(f"   Path: {path}")
                    print()
                    print("Testing: Press any key for 3 seconds...")
                    print()

                    import time
                    event_count = 0
                    start = time.time()

                    try:
                        for event in device.read_loop():
                            if time.time() - start > 3:
                                break
                            if event.type == ecodes.EV_KEY:
                                key_name = ecodes.KEY.get(event.code, f"KEY({event.code})")
                                state = "DOWN" if event.value == 1 else "UP"
                                print(f"  [{state}] {key_name}")
                                event_count += 1
                    except KeyboardInterrupt:
                        pass

                    print()
                    if event_count > 0:
                        print(f"✅ Received {event_count} key events!")
                        print("   The daemon WILL work from here!")
                    else:
                        print("❌ No key events received")
                        print("   The daemon won't work from this terminal")
                    break
        except:
            pass

except Exception as e:
    print(f"Error: {e}")

print()
print("=" * 70)
print()
print("Summary:")
if has_display:
    print("✅ You have a graphical display (DISPLAY or WAYLAND_DISPLAY is set)")
    print("   The daemon SHOULD be able to receive hotkeys from here")
else:
    print("❌ No graphical display detected")
    print("   Open XFCE4-terminal from your actual desktop")
