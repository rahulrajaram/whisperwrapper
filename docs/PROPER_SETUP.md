# Proper Setup and Usage of Hotkey Daemon

## Important Discovery

The hotkey daemon **cannot be tested from the same terminal where you're typing**. This is because terminal input goes through line discipline before reaching `/dev/input/event*` devices.

## Correct Setup

### Step 1: Start the Daemon in the Background

```bash
cd ~/Documents/whisper
sudo ./run_daemon.sh --debug &
```

This starts the daemon in the background. You'll see:
```
[2025-11-01 18:08:22] INFO: 🚀 Whisper Hotkey Daemon starting...
[2025-11-01 18:08:22] INFO: Using input device: AT Translated Set 2 keyboard (/dev/input/event0)
[2025-11-01 18:08:22] INFO: 🎧 Listening for hotkeys (CTRL+ALT+R to start/stop recording)
```

### Step 2: Leave That Terminal and Open a DIFFERENT Application

The daemon now needs to receive keyboard input from **outside the terminal it's running in**.

Try one of these:
- Open a **text editor** (gedit, code, vim, etc.)
- Open a **web browser**
- Open a **chat application**
- Click on any **other window**

### Step 3: Test the Hotkey

While the daemon is running in the background and you're in a **different application**, press **CTRL+ALT+R**.

The daemon should:
1. Print debug output in its terminal
2. Start recording audio
3. Listen for you to speak

### Step 4: Stop Recording

Press **ENTER** or **ESC** to stop recording. The transcription should appear in your clipboard.

Test with:
```bash
wl-paste
```

## Why This Matters

- ✅ Hotkeys work from web browsers, text editors, chat apps, anywhere
- ✅ Works even when terminal is minimized
- ✅ Works globally across the entire desktop
- ❌ Does NOT work when you're typing in the terminal running the daemon

This is actually the intended behavior! The daemon is designed to work system-wide, not just in one terminal.

## Proper Workflow

### Background Daemon (Recommended)

```bash
# Terminal 1: Start daemon in background
cd ~/Documents/whisper
sudo ./run_daemon.sh &

# Get back to your work in other applications
# Daemon keeps running and listening for CTRL+ALT+R

# When done, kill it:
sudo pkill -f whisper_hotkey_daemon.py
```

### Or: Systemd Service (Auto-start)

```bash
# One-time setup
mkdir -p ~/.config/systemd/user/
cat > ~/.config/systemd/user/whisper-hotkey.service << 'EOF'
[Unit]
Description=Whisper Hotkey Recording Daemon
After=graphical-session-pre.target

[Service]
Type=simple
ExecStart=%h/Documents/whisper/whisper_hotkey_daemon.py
Restart=on-failure

[Install]
WantedBy=graphical-session.target
EOF

systemctl --user daemon-reload
systemctl --user enable whisper-hotkey
systemctl --user start whisper-hotkey

# Then it starts automatically on login!
```

## Testing the Daemon Properly

1. **Start daemon:**
   ```bash
   sudo ./run_daemon.sh --debug &
   ```

2. **Open another application** (browser, text editor, etc.)

3. **Press CTRL+ALT+R** in that application

4. **Speak** into your microphone

5. **Press ENTER or ESC** to stop

6. **Check clipboard:**
   ```bash
   wl-paste
   ```

## Verification Checklist

✅ Daemon starts without errors
✅ You switch to a different application/window
✅ You press CTRL+ALT+R in that different window
✅ Daemon shows debug output for the key press
✅ Daemon shows "Starting voice recording"
✅ You speak into the microphone
✅ You press ENTER/ESC
✅ Daemon shows "Recording saved to clipboard"
✅ `wl-paste` shows your transcription

If all of these work, the daemon is functioning correctly!

## Common Mistakes

❌ **Testing while typing in the daemon terminal**
- The terminal input won't reach `/dev/input` devices
- Solution: Start daemon in background, switch to another app

❌ **Not using sudo**
- Many systems require sudo for `/dev/input` access
- Solution: Always use `sudo ./run_daemon.sh`

❌ **Testing CTRL+ALT+R by typing it**
- The terminal won't send these as key events to `/dev/input`
- Solution: Use an actual keyboard and press the keys physically

❌ **Expecting clipboard paste to happen automatically**
- The transcription is saved to clipboard, you must paste it
- Solution: Use CTRL+V or right-click paste after stopping recording

## Next Steps

Once the daemon is working:

1. **Run as background daemon:**
   ```bash
   cd ~/Documents/whisper
   sudo ./run_daemon.sh > ~/.whisper/daemon.log 2>&1 &
   ```

2. **Test real-world usage** - record voice in browsers, text editors, etc.

3. **Consider systemd setup** for auto-start on login

4. **Customize if needed** - change hotkey, model size, etc.

## If It Still Doesn't Work

Please verify:

1. Keyboard is working normally (can type in any application)
2. Microphone is working (`arecord -l` shows devices)
3. Running with `sudo`
4. Testing from a **different application** than the daemon terminal
5. All dependencies installed (`python3-evdev`, `whisper`, clipboard tools)

Report your findings!
