# Debugging the Hotkey Daemon

If the hotkey daemon isn't working, follow these steps in order.

## Step 1: Check Event Types

```bash
cd ~/Documents/whisper
sudo ./event_type_checker.py
```

Press CTRL+ALT+R and watch the output.

**Expected:**
```
✅ EV_KEY: code=29, value=1    (CTRL pressed)
✅ EV_KEY: code=100, value=1   (ALT pressed or code=56)
✅ EV_KEY: code=19, value=1    (R pressed)
```

**If you see:**
- `⚠️  OTHER:` instead of `✅ EV_KEY:` → The events aren't KEY events
- Nothing at all → Keyboard not being detected
- Different codes → Your keyboard layout is different

## Step 2: Check Raw Event Codes

```bash
sudo ./raw_event_monitor.py
```

Press CTRL+ALT+R. This shows the exact keycodes your keyboard sends.

**Record the codes you see** - they should match what event_type_checker showed.

## Step 3: Test Simple Hotkey Detection

```bash
sudo ./simple_hotkey_test.py
```

This mimics the daemon's hotkey detection logic exactly.

**Expected output when pressing CTRL+ALT+R:**
```
[KEY PRESS] KEY_LEFTCTRL | Pressed: {'KEY_LEFTCTRL'}
[KEY PRESS] KEY_LEFTALT | Pressed: {'KEY_LEFTCTRL', 'KEY_LEFTALT'}
[KEY PRESS] KEY_R | Pressed: {'KEY_LEFTCTRL', 'KEY_LEFTALT', 'KEY_R'}

🎯🎯🎯 CTRL+ALT+R DETECTED! 🎯🎯🎯

✅ SUCCESS! The hotkey detection works!
```

If this works, the daemon SHOULD work too.

## Step 4: Test the Daemon with Full Debug

```bash
sudo ./run_daemon.sh --debug 2>&1 | head -50
```

You should see:
```
[2025-11-01 18:08:22] INFO: 🚀 Whisper Hotkey Daemon starting...
[2025-11-01 18:08:22] INFO: Using input device: AT Translated Set 2 keyboard (/dev/input/event0)
[2025-11-01 18:08:22] INFO: 🎧 Listening for hotkeys (CTRL+ALT+R to start/stop recording)
[2025-11-01 18:08:22] INFO: Press Ctrl+C to exit
[2025-11-01 18:08:22] INFO: Opened device: AT Translated Set 2 keyboard
DEBUG: Device grabbed exclusively
```

Now press CTRL+ALT+R. You should see:
```
DEBUG: [RAW] type=1, code=29, name=KEY_LEFTCTRL, value=1
DEBUG: [KEY PRESS] KEY_LEFTCTRL | Pressed: {'KEY_LEFTCTRL'}
DEBUG: [RAW] type=1, code=100, name=KEY_LEFTALT, value=1
DEBUG: [KEY PRESS] KEY_LEFTALT | Pressed: {'KEY_LEFTCTRL', 'KEY_LEFTALT'}
DEBUG: [RAW] type=1, code=19, name=KEY_R, value=1
DEBUG: [KEY PRESS] KEY_R | Pressed: {'KEY_LEFTCTRL', 'KEY_LEFTALT', 'KEY_R'}
🎯 CTRL+ALT+R detected!
[2025-11-01 18:08:25] INFO: 🎤 Starting voice recording...
```

## Troubleshooting Matrix

| Symptom | Check | Solution |
|---------|-------|----------|
| event_type_checker shows no EV_KEY events | Running as root? | Try without sudo or with different keyboard |
| simple_hotkey_test doesn't detect CTRL+ALT+R | Your keyboard layout | Might need custom hotkey code |
| Daemon starts but no events logged | Device grab failing? | Try different event device (event1, event2, etc) |
| Events logged but no hotkey detected | Key name mismatch | Log the actual key names being received |
| Hotkey triggers but no recording | whisper_cli.py issue | Test `./whisper_cli.py --headless` directly |
| Recording works but no clipboard | Clipboard tool missing | Install wl-clipboard or xclip |

## If Nothing Works

1. **Check your keyboard layout:**
   ```bash
   setxkbmap -query
   ```

2. **Try a different input device:**
   ```bash
   sudo ./event_type_checker.py /dev/input/event9
   sudo ./event_type_checker.py /dev/input/event14
   # etc - try each device
   ```

3. **Check if X11 vs Wayland matters:**
   ```bash
   echo $DISPLAY      # X11
   echo $WAYLAND_DISPLAY  # Wayland
   ```

4. **Test whisper_cli.py directly:**
   ```bash
   ./whisper_cli.py --headless
   # Press ENTER to start, ENTER to stop
   ```

5. **Check clipboard:**
   ```bash
   wl-paste
   ```

## Advanced: Manual Testing

If you want to test a specific device:

```bash
# Monitor specific event device
sudo ./event_type_checker.py /dev/input/event8

# Or edit run_daemon.sh to hardcode the device:
export KEYBOARD_DEVICE=/dev/input/event8
sudo ./run_daemon.sh --debug
```

## Getting Help

When reporting an issue, include:

1. Output from `./event_type_checker.py` (showing actual keycodes)
2. Output from `./simple_hotkey_test.py` (did CTRL+ALT+R detect?)
3. Full daemon debug output: `sudo ./run_daemon.sh --debug 2>&1 | head -100`
4. Your keyboard model
5. Your display server: `echo $DISPLAY $WAYLAND_DISPLAY`
