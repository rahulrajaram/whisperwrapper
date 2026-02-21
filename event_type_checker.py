#!/usr/bin/env python3
"""
Check what event types are being received
"""

import sys
from evdev import InputDevice, ecodes

device_path = "/dev/input/event0"

print(f"Monitoring {device_path}")
print("Press keys and watch the event types...")
print()

try:
    device = InputDevice(device_path)
    print(f"Device: {device.name}\n")

    for event in device.read_loop():
        # Print ALL events, not just KEY events
        if event.type == ecodes.EV_KEY:
            print(f"✅ EV_KEY: code={event.code}, value={event.value}")
        elif event.type == ecodes.EV_SYN:
            print(f"   EV_SYN: code={event.code}, value={event.value}")
        else:
            print(f"⚠️  OTHER: type={event.type}, code={event.code}, value={event.value}")

except KeyboardInterrupt:
    print("\nExiting...")
except Exception as e:
    print(f"Error: {e}")
