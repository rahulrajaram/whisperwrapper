# Running the Whisper Hotkey Daemon

## Important: Terminal Access

The hotkey daemon **needs to run in a terminal with access to the input devices**. This means:

❌ **Does NOT work from:**
- Claude Code / IDE terminals
- SSH sessions (unless X11 forwarding is enabled)
- Containers without `/dev/input` access

✅ **Works from:**
- Your actual desktop terminal (GNOME Terminal, Konsole, Alacritty, etc.)
- A terminal opened directly on your desktop
- Any terminal that can access `/dev/input/event*`

## Quick Start

### 1. Open your actual desktop terminal
Click on your terminal application in your applications menu or taskbar.

**NOT** from within Claude Code or an IDE terminal.

### 2. Run the daemon

```bash
cd ~/Documents/whisper
./run_daemon.sh
```

Or with debug output:

```bash
./run_daemon.sh --debug
```

You should see:
```
[2025-11-01 18:08:22] INFO: 🚀 Whisper Hotkey Daemon starting...
[2025-11-01 18:08:22] INFO: Using input device: AT Translated Set 2 keyboard (/dev/input/event0)
[2025-11-01 18:08:22] INFO: 🎧 Listening for hotkeys (CTRL+ALT+R to start/stop recording)
[2025-11-01 18:08:22] INFO: Press Ctrl+C to exit
```

### 3. Test from any window
Once the daemon is running, press **CTRL+ALT+R** from anywhere on your desktop to start recording.

You should see in the terminal:
```
[KEY PRESS] KEY_LEFTCTRL | Pressed: {'KEY_LEFTCTRL'}
[KEY PRESS] KEY_LEFTALT | Pressed: {'KEY_LEFTCTRL', 'KEY_LEFTALT'}
[KEY PRESS] KEY_R | Pressed: {'KEY_LEFTCTRL', 'KEY_LEFTALT', 'KEY_R'}
🎯 CTRL+ALT+R detected!
[2025-11-01 18:08:50] INFO: 🎤 Starting voice recording...
```

### 4. Stop recording
Press **ENTER** or **ESC** to stop recording:

```
[KEY PRESS] KEY_ENTER | Pressed: {'KEY_ENTER'}
ENTER/ESC detected while recording
[2025-11-01 18:08:55] INFO: ⏹️  Stopping recording and saving to clipboard...
[2025-11-01 18:08:58] INFO: ✅ Recording saved to clipboard
```

### 5. Check the clipboard
The transcription should now be in your clipboard:

```bash
# Wayland
wl-paste

# X11
xclip -selection clipboard -o
```

## Running as a Systemd Service (Auto-start on Login)

To have the daemon start automatically when you log in:

### 1. Create the systemd service

```bash
mkdir -p ~/.config/systemd/user/
```

Create `~/.config/systemd/user/whisper-hotkey.service`:

```ini
[Unit]
Description=Whisper Hotkey Recording Daemon
After=graphical-session-pre.target

[Service]
Type=simple
ExecStart=%h/Documents/whisper/run_daemon.sh
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical-session.target
```

### 2. Enable and start

```bash
systemctl --user daemon-reload
systemctl --user enable whisper-hotkey
systemctl --user start whisper-hotkey
```

### 3. Check status

```bash
systemctl --user status whisper-hotkey
```

### 4. View logs

```bash
journalctl --user -u whisper-hotkey -f
```

## Troubleshooting

### "Permission denied" or no keyboard events

This usually means you're running from an IDE/SSH terminal. Solution:
1. Open your actual desktop terminal
2. Run from there instead

### Daemon starts but hotkeys don't work

Check that you can see keyboard events:

```bash
cd ~/Documents/whisper
./debug_key_events.py
```

Press some keys. If you see the events printed, the daemon should work.

### Still not working?

1. Make sure you're in a real desktop terminal:
   ```bash
   echo $DISPLAY
   ```
   Should show something like `:1` or `:0` (not empty)

2. Check group membership:
   ```bash
   groups $USER | grep input
   ```
   Should show `input` in the list

3. Run the daemon with full debug:
   ```bash
   ./run_daemon.sh --debug
   ```
   Then press keys and watch the output carefully

## Background Operation

### Run as background process

```bash
./run_daemon.sh &
```

Then you can use your terminal for other things. The daemon will continue running.

To stop it:
```bash
pkill -f whisper_hotkey_daemon.py
```

### Run with output to log file

```bash
./run_daemon.sh > ~/.whisper/hotkey-daemon.log 2>&1 &
```

Then monitor with:
```bash
tail -f ~/.whisper/hotkey-daemon.log
```

## Next Steps

Once the daemon is running successfully:

1. Try recording from different applications (browser, text editor, etc.)
2. Test that the transcription appears in clipboard
3. Consider setting it up as a systemd service for auto-start
4. Customize the hotkey if needed (see HOTKEY_DAEMON_README.md)

## Common Hotkey Uses

With the daemon running, you can now:

**In a web browser:** CTRL+ALT+R → type message → ENTER → paste

**In a text editor:** CTRL+ALT+R → dictate → ENTER → transcript appears in clipboard

**In chat applications:** CTRL+ALT+R → speak → ENTER → paste in chat

**Anywhere:** Quick voice-to-text conversion with one hotkey!
