# Testing the Hotkey Daemon

## Quick Test

### 1. Stop any running daemon
```bash
killall whisper_hotkey_daemon.py 2>/dev/null || true
```

### 2. Start the daemon with debug output
```bash
./whisper_hotkey_daemon.py --debug
```

You should see:
```
[2025-11-01 18:04:43] INFO: 🚀 Whisper Hotkey Daemon starting...
[2025-11-01 18:04:43] DEBUG: Using input device: AT Translated Set 2 keyboard (/dev/input/event0)
[2025-11-01 18:04:43] INFO: 🎧 Listening for hotkeys (CTRL+ALT+R to start/stop recording)
[2025-11-01 18:04:43] INFO: Press Ctrl+C to exit
```

### 3. Test the hotkey in another terminal

#### Option A: Real keyboard
Simply press **CTRL+ALT+R** on your actual keyboard. Then press **RETURN** or **ESC** to stop.

#### Option B: Debug script (requires keyboard device access)
```bash
# Open another terminal
./debug_key_events.py
```

This will show you all key events and highlight when CTRL+ALT+R is detected.

#### Option C: Event injection (requires root/sudo)
In another terminal:
```bash
# Test CTRL+ALT+R press
sudo ./inject_hotkey.py test-record

# Test RETURN press (to stop recording)
sudo ./inject_hotkey.py test-stop

# Full test sequence
sudo ./inject_hotkey.py test-sequence
```

## Expected Behavior

### When you press CTRL+ALT+R:
The daemon should output:
```
DEBUG: Key pressed: KEY_LEFTCTRL, Currently pressed: {'KEY_LEFTCTRL'}
DEBUG: Key pressed: KEY_LEFTALT, Currently pressed: {'KEY_LEFTCTRL', 'KEY_LEFTALT'}
DEBUG: Key pressed: KEY_R, Currently pressed: {'KEY_LEFTCTRL', 'KEY_LEFTALT', 'KEY_R'}
DEBUG: 🎯 CTRL+ALT+R detected!
[2025-11-01 18:04:50] INFO: 🎤 Starting voice recording...
```

### When recording, press RETURN or ESC:
```
DEBUG: Key pressed: KEY_RETURN, Currently pressed: {'KEY_RETURN'}
DEBUG: RETURN/ESC detected while recording
[2025-11-01 18:04:55] INFO: ⏹️  Stopping recording and saving to clipboard...
[2025-11-01 18:04:58] INFO: ✅ Recording saved to clipboard
```

## Troubleshooting

### "No keyboard device found"
Run the diagnostic:
```bash
./diagnose_hotkey.py
```

### Keys not being detected
The daemon logs all key presses with debug output. Check the debug output when you press keys.

If nothing appears when you press keys:
1. Try using a different keyboard device (change event0 to event1, event2, etc.)
2. Run `debug_key_events.py` to verify your keyboard is working

### Recording starts but doesn't transcribe
Check your microphone:
```bash
# Test microphone directly
./whisper_cli.py --headless
# Press ENTER to start, ENTER again to stop
```

### Clipboard not working
Check which clipboard tool is being used:
```bash
which wl-copy xclip xsel
```

The daemon tries them in order: wl-copy, xclip, xsel

## Testing Checklist

- [ ] Daemon starts without errors
- [ ] Daemon shows "Listening for hotkeys"
- [ ] Pressing CTRL+ALT+R starts recording (shows "🎤 Starting voice recording")
- [ ] Pressing RETURN/ESC stops recording (shows "⏹️  Stopping recording")
- [ ] Transcription appears in clipboard
- [ ] Can paste the transcription (CTRL+V in any text field)

## Advanced Testing

### Monitor clipboard contents
After recording, check what was saved:
```bash
# Wayland
wl-paste

# X11
xclip -selection clipboard -o
```

### Test with specific device
If you want to test a specific keyboard device:
```bash
# Edit the daemon to hardcode the device path, or create a wrapper:
KEYBOARD_DEVICE=/dev/input/event3 ./whisper_hotkey_daemon.py --debug
```

## Debug Output Example

Here's what you should see when everything is working:

```
[2025-11-01 18:04:43] INFO: 🚀 Whisper Hotkey Daemon starting...
DEBUG: Searching for keyboard device...
DEBUG: list_devices() returned empty, scanning /dev/input directly...
DEBUG: Checking /dev/input/event0: AT Translated Set 2 keyboard
DEBUG: Found keyboard: AT Translated Set 2 keyboard (/dev/input/event0)
[2025-11-01 18:04:43] INFO: Using input device: AT Translated Set 2 keyboard (/dev/input/event0)
[2025-11-01 18:04:43] INFO: 🎧 Listening for hotkeys (CTRL+ALT+R to start/stop recording)
[2025-11-01 18:04:43] INFO: Press Ctrl+C to exit
[2025-11-01 18:04:43] INFO: Opened device: AT Translated Set 2 keyboard

# User presses CTRL+ALT+R:
DEBUG: Key pressed: KEY_LEFTCTRL, Currently pressed: {'KEY_LEFTCTRL'}
DEBUG: Key pressed: KEY_LEFTALT, Currently pressed: {'KEY_LEFTCTRL', 'KEY_LEFTALT'}
DEBUG: Key pressed: KEY_R, Currently pressed: {'KEY_LEFTCTRL', 'KEY_LEFTALT', 'KEY_R'}
DEBUG: 🎯 CTRL+ALT+R detected!
[2025-11-01 18:04:50] INFO: 🎤 Starting voice recording...

# User speaks, then presses RETURN:
DEBUG: Key pressed: KEY_RETURN, Currently pressed: {'KEY_RETURN'}
DEBUG: RETURN/ESC detected while recording
[2025-11-01 18:04:55] INFO: ⏹️  Stopping recording and saving to clipboard...
[2025-11-01 18:04:58] INFO: ✅ Recording saved to clipboard
```

If you see this, everything is working correctly!
