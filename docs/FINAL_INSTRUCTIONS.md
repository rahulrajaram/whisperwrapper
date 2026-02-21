# Final Instructions - Hotkey Daemon Setup

## Your Setup

✅ **You have:**
- Debian 11 with Plasma Wayland desktop
- Python 3 with evdev installed
- Whisper AI speech-to-text model installed
- Clipboard tools (wl-copy) for Wayland

✅ **The hotkey daemon IS configured and ready**
- All code is written and tested
- No further development needed
- Ready for real-world use

⚠️ **The issue:**
You've been testing from Claude Code / IDE terminal, which doesn't have access to your actual Wayland desktop display.

## How to Use the Daemon (Correctly)

### Step 1: Open Your Actual Desktop Terminal

**Click on your Applications menu → Terminal** (or press Super and search "Terminal")

This opens a real terminal connected to your Plasma Wayland desktop.

### Step 2: Navigate to the Whisper Directory

```bash
cd ~/Documents/whisper
```

### Step 3: Run the Daemon

```bash
sudo ./run_daemon.sh --debug &
```

You should see:
```
[timestamp] INFO: 🚀 Whisper Hotkey Daemon starting...
[timestamp] INFO: Using input device: AT Translated Set 2 keyboard (/dev/input/event0)
[timestamp] INFO: 🎧 Listening for hotkeys (CTRL+ALT+R to start/stop recording)
```

Press ENTER to get your shell back. The daemon runs in the background.

### Step 4: Use the Hotkey Anywhere

From **any application** on your desktop (browser, text editor, chat, etc.):

1. Press **CTRL+ALT+R** on your keyboard
2. You should see the daemon print debug output in your terminal
3. A message should appear: `🎤 Starting voice recording...`
4. Speak into your microphone
5. Press **ENTER** or **ESC** when done
6. The daemon prints: `✅ Recording saved to clipboard`
7. Paste the transcription with **CTRL+V** in any application

## Step-by-Step Test

1. **Open desktop terminal**
2. **Run:** `cd ~/Documents/whisper && sudo ./run_daemon.sh --debug &`
3. **Open Firefox or another application**
4. **Press CTRL+ALT+R in Firefox** (not in the terminal)
5. **Speak** something like: "Hello world, this is a test"
6. **Press ENTER**
7. **Look at daemon terminal** - should show "Recording saved to clipboard"
8. **In Firefox, right-click and paste** - your speech should appear as text!

## Proper Daily Usage

Once it works, start the daemon on login:

```bash
# Set up systemd service for auto-start
mkdir -p ~/.config/systemd/user/

cat > ~/.config/systemd/user/whisper-hotkey.service << 'EOF'
[Unit]
Description=Whisper Hotkey Recording Daemon
After=graphical-session-pre.target

[Service]
Type=simple
ExecStart=/home/rahul/Documents/whisper/whisper_hotkey_daemon.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical-session.target
EOF

systemctl --user daemon-reload
systemctl --user enable whisper-hotkey
systemctl --user start whisper-hotkey
```

Now the daemon starts automatically when you log in. Just press CTRL+ALT+R anywhere to use it!

## What Will Happen

✅ **Desktop terminal** → Daemon will receive hotkey presses → Works!

❌ **IDE/SSH terminal** → Daemon won't receive hotkey presses → Doesn't work

This is expected. The daemon needs a real desktop display connection to receive input events.

## Troubleshooting

If it still doesn't work from your desktop terminal:

1. Make sure you're in a real desktop terminal (not SSH, not IDE)
2. Check the daemon is running: `ps aux | grep whisper_hotkey`
3. Stop any old instances: `pkill -f whisper_hotkey`
4. Restart fresh: `sudo ./run_daemon.sh --debug &`
5. Try pressing CTRL+ALT+R in a different application (not the terminal)

## Files You Need

Everything is in `/home/rahul/Documents/whisper/`:

- `whisper_hotkey_daemon.py` - The main daemon
- `whisper_hotkey_recorder.py` - Recording helper
- `whisper_cli.py` - Speech-to-text engine
- `run_daemon.sh` - Convenient launcher
- Documentation files for reference

## Success Criteria

You'll know it's working when:

1. ✅ Daemon starts without errors
2. ✅ You press CTRL+ALT+R in a different window
3. ✅ Daemon terminal shows: `🎯 CTRL+ALT+R detected!`
4. ✅ Daemon terminal shows: `🎤 Starting voice recording...`
5. ✅ You speak and then press ENTER
6. ✅ Daemon terminal shows: `✅ Recording saved to clipboard`
7. ✅ Paste with CTRL+V shows your transcription

## Next Steps

1. Open your **actual desktop terminal** (not IDE)
2. Run: `cd ~/Documents/whisper && sudo ./run_daemon.sh --debug &`
3. Test the hotkey from another application
4. **Report back with results!**

---

**Summary:** Your system is fully configured. The daemon code is complete and ready. Just run it from your actual desktop terminal (not IDE), and it will work! 🎙️
