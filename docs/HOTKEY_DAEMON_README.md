# Whisper Hotkey Daemon

Global hotkey voice recording daemon for Linux (Wayland/X11 compatible).

## Features

- **Global Hotkey Support**: CTRL+ALT+R works from anywhere on your desktop
- **One-Press Recording**: Toggles recording on/off with single hotkey
- **Quick Stop**: Press RETURN or ESC to stop recording
- **Clipboard Integration**: Transcription automatically saved to system clipboard
- **Wayland Compatible**: Works on modern Wayland compositors (GNOME, KDE, Sway)
- **X11 Compatible**: Also works on X11 if you prefer
- **Debug Mode**: Optional verbose logging for troubleshooting

## Requirements

- Python 3.7+
- Debian/Ubuntu or compatible Linux distribution
- Wayland or X11 display server
- Microphone configured and working
- Clipboard utility (wl-copy for Wayland, xclip for X11)

## Installation

### 1. Run the setup script

```bash
cd ~/Documents/whisper
chmod +x setup_hotkey.sh
./setup_hotkey.sh
```

This will:
- Install required Python packages (python3-evdev)
- Install clipboard utilities (wl-clipboard, xclip)
- Configure udev rules for keyboard access
- Set proper file permissions

### 2. Log out and log back in

The setup script adds your user to the `input` group. You must log out and log back in for this to take effect.

**Or**, reload your group membership immediately with:

```bash
newgrp input
```

### 3. Test the daemon

```bash
cd ~/Documents/whisper
./whisper_hotkey_daemon.py --debug
```

You should see:

```
[2024-01-15 14:23:45] INFO: 🚀 Whisper Hotkey Daemon starting...
[2024-01-15 14:23:45] INFO: Using keyboard: AT Translated Set 2 keyboard (/dev/input/event3)
[2024-01-15 14:23:45] INFO: 🎧 Listening for hotkeys (CTRL+SHIFT+R to start/stop recording)
```

## Usage

### Basic Operation

1. **Start Recording**: Press `CTRL+ALT+R`
   - You'll see a message: `🎤 Starting voice recording...`
   - Speak into your microphone

2. **Stop Recording**: Press `RETURN` or `ESC`
   - Recording stops automatically
   - Transcription is saved to your clipboard
   - You'll see: `✅ Recording saved to clipboard`

3. **Stop Daemon**: Press `CTRL+C` in the terminal

### Command Line Options

```bash
# Run normally
./whisper_hotkey_daemon.py

# Run with debug output (recommended for first-time testing)
./whisper_hotkey_daemon.py --debug

# Run in background
./whisper_hotkey_daemon.py &

# Run as daemon and redirect output to log file
./whisper_hotkey_daemon.py > ~/.whisper/hotkey-daemon.log 2>&1 &
```

## Running as a Systemd Service (Optional)

To run the daemon automatically on login, create a systemd user service:

### 1. Create the service file

```bash
mkdir -p ~/.config/systemd/user/
```

Create `~/.config/systemd/user/whisper-hotkey.service`:

```ini
[Unit]
Description=Whisper Hotkey Recording Daemon
Documentation=file://%h/Documents/whisper/HOTKEY_DAEMON_README.md
After=graphical-session-pre.target

[Service]
Type=simple
ExecStart=%h/Documents/whisper/whisper_hotkey_daemon.py
Restart=on-failure
RestartSec=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=whisper-hotkey

[Install]
WantedBy=graphical-session-pre.target
```

### 2. Enable and start the service

```bash
systemctl --user daemon-reload
systemctl --user enable whisper-hotkey
systemctl --user start whisper-hotkey
```

### 3. Check status

```bash
systemctl --user status whisper-hotkey
journalctl --user -u whisper-hotkey -f
```

### 4. Manage the service

```bash
# Stop the daemon
systemctl --user stop whisper-hotkey

# Restart the daemon
systemctl --user restart whisper-hotkey

# View logs
journalctl --user -u whisper-hotkey --since "10 minutes ago"

# Disable auto-start on login
systemctl --user disable whisper-hotkey
```

## Architecture

### Components

1. **whisper_hotkey_daemon.py** - Main hotkey listener
   - Monitors keyboard input at the system level
   - Detects CTRL+SHIFT+R hotkey press
   - Spawns recording process on hotkey
   - Terminates recording on RETURN/ESC

2. **whisper_hotkey_recorder.py** - Recording helper
   - Performs actual audio recording
   - Runs Whisper transcription
   - Copies result to clipboard
   - Runs in subprocess for clean isolation

3. **whisper_cli.py** - Core recording and transcription
   - Handles microphone interaction
   - Performs Whisper speech-to-text
   - Original CLI functionality preserved

### How It Works

```
┌─────────────────────────────────────────┐
│  whisper_hotkey_daemon.py              │
│  (Monitors /dev/input/event*)          │
│                                         │
│  ┌─────────────────────────────────┐  │
│  │ KeyListener (main thread)       │  │
│  │                                 │  │
│  │ CTRL+SHIFT+R → spawn recorder  │  │
│  │ RETURN/ESC   → stop recorder   │  │
│  └─────────────────────────────────┘  │
└─────────────────────────────────────────┘
                  │
                  │ spawn
                  ▼
┌─────────────────────────────────────────┐
│  whisper_hotkey_recorder.py             │
│  (subprocess)                           │
│                                         │
│  ┌─────────────────────────────────┐  │
│  │ WhisperCLI (headless mode)      │  │
│  │ - Record audio                  │  │
│  │ - Transcribe with Whisper       │  │
│  │ - Copy to clipboard             │  │
│  └─────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## Troubleshooting

### Permission Denied Error

If you see:
```
[ERROR] Permission denied! Make sure you're in the 'input' group:
  sudo usermod -a -G input $USER
```

**Solution:**
1. Verify you're in the input group: `groups $USER`
2. If not, run: `sudo usermod -a -G input $USER`
3. Log out and log back in completely
4. Verify: `groups $USER` should now show `input`

### No Keyboard Device Found

If you see:
```
[ERROR] No keyboard device found!
```

**Solution:**
1. Check available devices: `ls -la /dev/input/event*`
2. Run with debug: `./whisper_hotkey_daemon.py --debug`
3. This will show which devices are being checked
4. Make sure you're in the input group (see above)

### Hotkey Not Triggering

**Check:**
1. Is the daemon running? `ps aux | grep hotkey_daemon`
2. Is the hotkey registered? Run with `--debug` flag
3. Try the hotkey and watch the debug output
4. Check if another application is capturing the hotkey

**Debug Steps:**
```bash
# Run in debug mode
./whisper_hotkey_daemon.py --debug

# In another terminal, list input devices
evtest /dev/input/event3

# Try pressing CTRL+SHIFT+R and watch for key events
```

### No Audio Recorded

**Check:**
1. Is your microphone working? `arecord -l`
2. Does `whisper_cli.py --headless` work? Try it directly:
   ```bash
   ./whisper_cli.py --headless
   # Press ENTER to start, ENTER again to stop
   ```
3. Check microphone volume: `alsamixer`

### Clipboard Not Working

If transcription is not appearing in clipboard:

**Check which tool is available:**
```bash
which wl-copy    # Wayland
which xclip      # X11
which xsel       # X11 alternative
```

**Install missing tools:**
```bash
# For Wayland
sudo apt-get install wl-clipboard

# For X11
sudo apt-get install xclip xsel
```

### systemd Service Issues

**Check logs:**
```bash
journalctl --user -u whisper-hotkey -n 50
```

**Common issues:**
- Service not starting: Check the path in the .service file matches your setup
- Permission denied: Make sure udev rules are set up correctly
- Can't find modules: Make sure Python path is set correctly

## Performance Considerations

- **CPU Usage**: Negligible when not recording (~0.1%)
- **Memory Usage**: ~50-100 MB while recording
- **Latency**: < 100ms from hotkey press to recording start
- **Compatibility**: Works with wireless keyboards and trackpads

## Security Notes

- The daemon requires access to `/dev/input/event*` devices
- This is necessary to detect hotkeys system-wide
- Access is restricted by udev rules and user group membership
- Only your user account can trigger recordings
- Transcriptions are stored locally in clipboard only

## Advanced Configuration

### Custom Hotkey

To change the hotkey from CTRL+SHIFT+R to something else, edit `whisper_hotkey_daemon.py`:

```python
# Around line 150, find this method:
def _is_hotkey_pressed(self, device, current_keycode, target_keycode):
    if current_keycode != target_keycode:
        return False
    # ...

# And modify the hotkey check in handle_key_event():
# Change from:
if self._is_hotkey_pressed(device, keycode, ecodes.KEY_R):
# To your desired key (e.g., KEY_V for CTRL+SHIFT+V)
```

### Running Multiple Instances

You can run multiple daemon instances for different hotkeys:

```bash
# Daemon 1 (CTRL+SHIFT+R for main recording)
./whisper_hotkey_daemon.py

# Daemon 2 (Different hotkey for translation, requires custom code)
./whisper_hotkey_daemon_translate.py
```

## Performance Tuning

### For Low-End Systems

If your system is slow, you can:

1. Use the smaller Whisper model:
   - Edit `whisper_cli.py` line 30: `self.model = whisper.load_model("tiny")`
   - Faster but less accurate

2. Reduce audio chunk size:
   - Edit `whisper_cli.py` line 37: `self.chunk = 2048`
   - Lower latency but uses more CPU during recording

### For High Accuracy

1. Use the larger Whisper model:
   - Edit `whisper_cli.py` line 30: `self.model = whisper.load_model("large")`
   - Slower but more accurate

## Contributing & Support

For issues or feature requests, see the main repository documentation.

## License

Same as the main Whisper CLI project.
