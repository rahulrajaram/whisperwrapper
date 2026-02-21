#!/usr/bin/env python3
"""
Test if the hotkey CTRL+ALT+R is being captured by the desktop environment
or if it's available for our daemon to use
"""

import sys
import subprocess

print("🔍 Hotkey Capture Test")
print("=" * 70)
print()

# Check if XFCE or Plasma might be using CTRL+ALT+R
print("Checking for conflicting hotkey bindings...")
print()

# Common locations for XFCE hotkey configs
xfce_files = [
    "~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-keyboard-shortcuts.xml",
    "~/.config/xfce4/xfconf/xfce-perchannel-xml/xfwm4.xml",
]

plasma_files = [
    "~/.config/kglobalshortcutsrc",
]

all_files = xfce_files + plasma_files

import os
for file_path in all_files:
    expanded = os.path.expanduser(file_path)
    if os.path.exists(expanded):
        print(f"✅ Found: {file_path}")

        # Search for CTRL+ALT+R in the file
        try:
            with open(expanded, 'r') as f:
                content = f.read()
                if 'Alt+Ctrl+R' in content or 'Ctrl+Alt+R' in content or '<Alt>R' in content:
                    print(f"   ⚠️  File mentions Alt+R combinations!")
                    # Show the relevant lines
                    for i, line in enumerate(content.split('\n')):
                        if 'Alt' in line and 'R' in line:
                            print(f"   Line {i+1}: {line.strip()}")
        except Exception as e:
            print(f"   Error reading: {e}")
    else:
        print(f"❌ Not found: {file_path}")

print()
print("=" * 70)
print()
print("Next Steps:")
print()
print("1. Check if XFCE4 has CTRL+ALT+R bound to something:")
print("   Settings Manager → Keyboard → Application Shortcuts")
print()
print("2. Check Plasma shortcuts:")
print("   System Settings → Shortcuts → Global Shortcuts")
print()
print("3. If CTRL+ALT+R is already bound, either:")
print("   - Unbind it from the desktop environment")
print("   - Use a different hotkey (edit whisper_hotkey_daemon.py)")
print()
print("4. Try a different hotkey to test:")
print("   - CTRL+ALT+V (Voice)")
print("   - Super+Shift+R (if available)")
print("   - CTRL+ALT+M (Mic)")
