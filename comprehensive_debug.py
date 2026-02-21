#!/usr/bin/env python3
"""
Comprehensive debugging tool for the hotkey daemon
Tests all components step by step
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_evdev_import():
    """Test if evdev can be imported"""
    section("1. Testing evdev import")
    try:
        from evdev import InputDevice, list_devices, ecodes
        print("✅ evdev imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import evdev: {e}")
        return False

def test_device_listing():
    """Test if devices can be listed"""
    section("2. Testing device listing")
    try:
        from evdev import list_devices, InputDevice

        devices = list_devices()
        print(f"✅ list_devices() returned {len(devices)} devices")

        if not devices:
            print("⚠️  list_devices() returned empty, checking /dev/input directly...")
            import glob
            devices = glob.glob("/dev/input/event*")
            print(f"✅ Found {len(devices)} devices via glob")

        # Try to open each
        accessible = 0
        for path in devices[:10]:
            try:
                device = InputDevice(path)
                print(f"  ✅ {path}: {device.name}")
                accessible += 1
            except PermissionError:
                print(f"  ❌ {path}: Permission denied")
            except Exception as e:
                print(f"  ⚠️  {path}: {e}")

        if accessible > 0:
            print(f"\n✅ Successfully accessed {accessible} devices")
            return True
        else:
            print("\n❌ Could not access any devices")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_keyboard_detection():
    """Test keyboard detection"""
    section("3. Testing keyboard device detection")
    try:
        from evdev import InputDevice, ecodes
        import glob

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
                        print(f"✅ Found keyboard: {device.name} ({path})")
            except:
                pass

        if keyboards:
            print(f"\n✅ Found {len(keyboards)} keyboard device(s)")
            return True, keyboards
        else:
            print("\n❌ No keyboard devices found")
            return False, []

    except Exception as e:
        print(f"❌ Error: {e}")
        return False, []

def test_read_key_events(device_path):
    """Test reading actual key events from a device"""
    section("4. Testing key event reading")
    print(f"Using device: {device_path}")
    print("Press some keys on your keyboard (5 second timeout)...\n")

    try:
        from evdev import InputDevice, ecodes

        device = InputDevice(device_path)
        print(f"Opened: {device.name}\n")

        events_received = 0
        start_time = time.time()

        for event in device.read_loop():
            if time.time() - start_time > 5:
                break

            if event.type == ecodes.EV_KEY:
                try:
                    key_name = ecodes.KEY.get(event.code, f"UNKNOWN({event.code})")
                except:
                    key_name = f"KEY({event.code})"

                state = "PRESS" if event.value == 1 else "RELEASE"
                print(f"  {state}: {key_name}")
                events_received += 1

        if events_received > 0:
            print(f"\n✅ Received {events_received} key events")
            return True
        else:
            print("\n⚠️  No key events received in 5 seconds")
            print("    This suggests the daemon won't receive keyboard input either")
            return False

    except PermissionError:
        print("❌ Permission denied")
        print("   You may not be in the 'input' group or your session doesn't have access")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_ctrl_alt_r_detection(device_path):
    """Test CTRL+ALT+R detection logic"""
    section("5. Testing CTRL+ALT+R detection logic")
    print(f"Using device: {device_path}")
    print("Press CTRL+ALT+R (5 second timeout)...\n")

    try:
        from evdev import InputDevice, ecodes

        device = InputDevice(device_path)
        pressed_keys = set()
        detected = False

        start_time = time.time()

        for event in device.read_loop():
            if time.time() - start_time > 5:
                break

            if event.type != ecodes.EV_KEY:
                continue

            try:
                key_name = ecodes.KEY.get(event.code, f"UNKNOWN({event.code})")
            except:
                key_name = f"KEY({event.code})"

            if event.value == 1:  # Press
                pressed_keys.add(key_name)
                print(f"  Key pressed: {key_name}")
                print(f"    Currently pressed: {pressed_keys}")

                # Check for CTRL+ALT+R
                if key_name == 'KEY_R':
                    has_ctrl = any(k in pressed_keys for k in ['KEY_LEFTCTRL', 'KEY_RIGHTCTRL'])
                    has_alt = any(k in pressed_keys for k in ['KEY_LEFTALT', 'KEY_RIGHTALT'])

                    if has_ctrl and has_alt:
                        print(f"\n✅ CTRL+ALT+R DETECTED!")
                        detected = True
                        break

            elif event.value == 0:  # Release
                pressed_keys.discard(key_name)

        if detected:
            print("\n✅ CTRL+ALT+R detection works!")
            return True
        else:
            print("\n⚠️  CTRL+ALT+R not detected in 5 seconds")
            print("    Try pressing it again, or check your keyboard")
            return False

    except PermissionError:
        print("❌ Permission denied")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_whisper_cli():
    """Test if whisper_cli.py works"""
    section("6. Testing Whisper CLI")
    whisper_cli = Path(__file__).parent / "whisper_cli.py"

    if not whisper_cli.exists():
        print(f"❌ {whisper_cli} not found")
        return False

    print(f"✅ {whisper_cli} exists")

    if not os.access(whisper_cli, os.X_OK):
        print(f"⚠️  {whisper_cli} is not executable")
        print("   Run: chmod +x whisper_cli.py")
    else:
        print(f"✅ {whisper_cli} is executable")

    return True

def test_clipboard():
    """Test clipboard functionality"""
    section("7. Testing clipboard tools")

    tools = {
        'wl-copy': 'Wayland',
        'xclip': 'X11',
        'xsel': 'X11',
    }

    found_tools = []
    for tool, system in tools.items():
        result = subprocess.run(['which', tool], capture_output=True)
        if result.returncode == 0:
            print(f"✅ {tool} ({system})")
            found_tools.append(tool)
        else:
            print(f"❌ {tool} ({system}) - not found")

    if found_tools:
        print(f"\n✅ Found {len(found_tools)} clipboard tool(s)")

        # Test one
        test_text = "Test clipboard from Whisper hotkey daemon"
        print(f"\nTesting '{found_tools[0]}' with text: '{test_text}'")

        try:
            process = subprocess.Popen(
                [found_tools[0]],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            process.communicate(input=test_text, timeout=2)

            if process.returncode == 0:
                print(f"✅ Clipboard write succeeded")
                return True
            else:
                print(f"❌ Clipboard write failed")
                return False
        except Exception as e:
            print(f"⚠️  Error testing clipboard: {e}")
            return False
    else:
        print("\n❌ No clipboard tools found")
        return False

def test_display_env():
    """Test display environment"""
    section("8. Testing display environment")

    display = os.environ.get('DISPLAY')
    wayland_display = os.environ.get('WAYLAND_DISPLAY')

    if display:
        print(f"✅ DISPLAY={display} (X11)")
    else:
        print(f"❌ DISPLAY not set (not using X11)")

    if wayland_display:
        print(f"✅ WAYLAND_DISPLAY={wayland_display}")
    else:
        print(f"⚠️  WAYLAND_DISPLAY not set (might be using Wayland)")

    if display or wayland_display:
        print("\n✅ Display environment looks good")
        return True
    else:
        print("\n❌ Neither DISPLAY nor WAYLAND_DISPLAY set")
        print("   This suggests you're not in a graphical session")
        return False

def main():
    print("🔍 Whisper Hotkey Daemon - Comprehensive Debug Tool")
    print("=" * 70)

    results = {}

    # Test 1: evdev import
    results['evdev'] = test_evdev_import()
    if not results['evdev']:
        print("\n❌ Cannot continue without evdev")
        return

    # Test 2: device listing
    results['devices'] = test_device_listing()

    # Test 3: keyboard detection
    results['keyboards_found'], keyboards = test_keyboard_detection()

    if not keyboards:
        print("\n❌ No keyboards found - cannot continue")
        return

    # Test 4: key event reading
    keyboard_path = keyboards[0][1]
    results['key_events'] = test_read_key_events(keyboard_path)

    if not results['key_events']:
        print("\n⚠️  Not receiving key events - the daemon won't work")
        print("   Possible causes:")
        print("    - Not running from a real desktop terminal")
        print("    - No keyboard connected or not working")
        print("    - Permission issues with /dev/input")
        return

    # Test 5: CTRL+ALT+R detection
    results['hotkey'] = test_ctrl_alt_r_detection(keyboard_path)

    # Test 6-8: Other components
    results['whisper'] = test_whisper_cli()
    results['clipboard'] = test_clipboard()
    results['display'] = test_display_env()

    # Summary
    section("SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"Passed: {passed}/{total} tests\n")

    for test, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test}")

    print()
    if passed == total:
        print("✅ All tests passed! The daemon should work.")
    elif results['key_events']:
        print("⚠️  Some tests failed but key events are working.")
        print("    The daemon should still function for CTRL+ALT+R.")
    else:
        print("❌ Key event reading failed - daemon won't work.")
        print("    Make sure you're running from an actual desktop terminal.")

if __name__ == "__main__":
    main()
