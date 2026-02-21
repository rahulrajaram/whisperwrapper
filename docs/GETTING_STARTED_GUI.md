# Getting Started with Whisper GUI

## ⚡ Quick Start (3 Steps)

### Step 1: Install PyQt6
```bash
pip install PyQt6
```

### Step 2: Run the Application
```bash
cd ~/Documents/whisper
./whisper_gui.py
```

### Step 3: Start Using It!
- Click **▶ Start Recording**
- Speak into your microphone
- Click **⏹ Stop Recording**
- Your transcription **automatically copies to clipboard** ✅
- History appears in the table below
- Paste with **Ctrl+V** in any application

Done! 🎉

---

## Detailed Usage

### Recording
1. Click the green **▶ Start Recording** button
2. The button becomes disabled (grayed out)
3. Status shows "🎤 Recording..."
4. Speak clearly at normal volume
5. Click **⏹ Stop Recording** when done
6. Wait for "Processing..." message
7. Transcription **automatically copies to clipboard** ✅
8. Transcription also appears in the history table below
9. Status shows "✅ Transcription copied to clipboard"
10. Paste with **Ctrl+V** in any application

### Managing History
- **Auto-Copy**: Latest transcription automatically goes to clipboard
- **View**: All transcriptions appear in the scrollable table
- **Manual Copy**: Click the "Copy" button in any row to copy that transcription
- **Clear**: Click "🗑 Clear History" to remove all entries
- **Export**: Manually copy from `~/.whisper/gui_history.json`

### Copying to Clipboard
- **Automatic**: When you stop recording, text is automatically copied
- **Manual**: Click "Copy" button for any history row
- **Paste**: Use **Ctrl+V** in any application

### Persistent History
- All transcriptions are automatically saved
- Located at: `~/.whisper/gui_history.json`
- Survives application restarts
- Can be manually edited or backed up

---

## Installation Options

### Option 1: Direct Execution (Easiest)
```bash
~/Documents/whisper/whisper_gui.py
```

### Option 2: Using Launcher Script
```bash
~/Documents/whisper/launch_gui.sh
```
(Automatically checks for dependencies)

### Option 3: From Application Menu
1. Press the Super key (Windows key)
2. Type "Whisper"
3. Click "Whisper Voice Recording"

### Option 4: Python Direct
```bash
python3 ~/Documents/whisper/whisper_gui.py
```

---

## Troubleshooting

### "No module named PyQt6"
**Solution:**
```bash
pip install PyQt6
```

### "Microphone not found"
**Solution 1**: Check microphone in terminal
```bash
python3 ~/Documents/whisper/whisper_cli.py --configure
```

**Solution 2**: Check volume levels
```bash
alsamixer
```

**Solution 3**: Check user permissions
```bash
# Make sure you're in the audio group
groups $USER | grep audio
```

### "Copy to clipboard not working"
**For Wayland (Plasma):**
```bash
sudo apt-get install wl-clipboard
```

**For X11 (XFCE):**
```bash
sudo apt-get install xclip
```

### "No audio is being recorded"
1. Check microphone is not muted
2. Check volume level in system settings
3. Test with built-in speaker first
4. Check microphone is properly connected

### "Application won't start"
```bash
# Check for errors
python3 -u ~/Documents/whisper/whisper_gui.py 2>&1 | head -20
```

### "Recording works but transcription fails with ffmpeg error"
When running the GUI as a systemd user service, ffmpeg may not be found even if installed.

**Solution:** Update the systemd service file to include system paths in PATH environment variable.

Edit `~/.config/systemd/user/whisper-gui.service` and change:
```ini
Environment="PATH=/home/rahul/Documents/whisper/venv/bin"
```

To:
```ini
Environment="PATH=/home/rahul/Documents/whisper/venv/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
```

Then reload and restart:
```bash
systemctl --user daemon-reload
systemctl --user restart whisper-gui.service
```

**Why:** The Whisper model uses ffmpeg to process audio files. Without the system paths in PATH, ffmpeg (located at `/usr/bin/ffmpeg`) cannot be found by the service.

---

## Tips & Tricks

### Keyboard Shortcuts
- Use Ctrl+Alt+Shift+R for global toggle (provided by the embedded HotkeyBackend)
- For desktop-managed shortcuts see `docs/SHORTCUT_SETUP.md`

### Better Transcription
- Speak clearly and at normal volume
- Minimize background noise
- Use a good quality microphone
- Keep your distance consistent from the mic

### Viewing History File
```bash
# View raw JSON
cat ~/.whisper/gui_history.json

# View formatted
python3 -m json.tool ~/.whisper/gui_history.json

# Count entries
python3 -c "import json; print(len(json.load(open(os.path.expanduser('~/.whisper/gui_history.json')))))"
```

### Backup History
```bash
# Simple copy
cp ~/.whisper/gui_history.json ~/whisper_history_backup.json

# With timestamp
cp ~/.whisper/gui_history.json ~/whisper_history_$(date +%Y%m%d_%H%M%S).json
```

---

## Features Explained

### Start Button
- Green button with ▶ symbol
- Click to begin recording
- Becomes disabled while recording
- Status updates to show recording in progress

### Stop Button
- Red button with ⏹ symbol
- Only enabled while recording
- Click to end recording and transcribe
- Waits for Whisper to process the audio

### History Table
- Shows all past transcriptions
- Newest entries at the top
- Three columns:
  - **Timestamp**: When you recorded it
  - **Transcription**: The full text
  - **Copy**: Button to copy to clipboard
- Scrollable for many entries
- Persists between application restarts

### Clear History Button
- Orange button with 🗑 symbol
- Removes all transcriptions
- Clears the history file
- Cannot be undone (but file is at `~/.whisper/gui_history.json`)

### Status Bar
- Bottom of window
- Shows real-time status
- Examples:
  - "Ready"
  - "Recording in progress..."
  - "Processing transcription..."
  - "✅ Copied to clipboard"
  - "✅ Recording saved"

---

## File Locations

```
~/Documents/whisper/
├── whisper_gui.py          ← Main application
├── launch_gui.sh           ← Launcher script
├── whisper_cli.py          ← Core recording logic
├── requirements.txt        ← Dependencies
├── WHISPER_GUI_README.md   ← Full documentation
├── SETUP_GUI.md           ← Setup instructions
└── GETTING_STARTED_GUI.md ← This file

~/.whisper/
└── gui_history.json        ← Your transcription history
```

---

## System Requirements

### Required
- Python 3.7 or higher
- PyQt6 library
- Microphone (any working input device)
- OpenAI Whisper model (auto-downloads on first use)

### Recommended
- Modern CPU (transcription is faster)
- 4GB+ RAM (Whisper model uses ~500MB)
- Good quality microphone

### Optional
- wl-clipboard (for Wayland clipboard support)
- xclip (for X11 clipboard support)

---

## First-Time Setup Checklist

- [ ] Install Python 3.7+
- [ ] Install PyQt6: `pip install PyQt6`
- [ ] Navigate to: `cd ~/Documents/whisper`
- [ ] Run application: `./whisper_gui.py`
- [ ] Test recording with your microphone
- [ ] Verify transcription appears
- [ ] Test copy-to-clipboard
- [ ] Check history file: `~/.whisper/gui_history.json`

---

## Advanced Usage

### Global Hotkeys
The GUI ships with a built-in `HotkeyBackend`, so pressing **Ctrl+Alt+Shift+R** toggles recording as soon as the window launches—no extra daemon required. If you’d rather let the desktop environment send signals (useful for Wayland), wire KDE/GNOME shortcuts to the `whisper-recording-toggle` helper described in `docs/SHORTCUT_SETUP.md`.

### Custom Configuration
The GUI uses your existing Whisper configuration from CLI.

To change microphone:
```bash
python3 ~/Documents/whisper/whisper_cli.py --configure
```

---

## Need Help?

### Read the Docs
1. **Quick setup**: `SETUP_GUI.md`
2. **Full guide**: `WHISPER_GUI_README.md`
3. **Architecture**: `GUI_SUMMARY.md`
4. **Implementation**: Look at code comments in `whisper_gui.py`

### Check Your System
```bash
# Python version
python3 --version

# PyQt6 installed?
python3 -c "import PyQt6; print('✅ PyQt6 OK')"

# Whisper working?
python3 -c "import whisper; print('✅ Whisper OK')"

# Microphone available?
python3 ~/Documents/whisper/whisper_cli.py --configure
```

### Common Issues
See **Troubleshooting** section above

---

## Summary

You now have a complete voice recording application that:
- ✅ Records audio from your microphone
- ✅ Transcribes to text using AI
- ✅ Saves history for later review
- ✅ Copies transcriptions to clipboard
- ✅ Integrates with your desktop

Enjoy! 🎤✨
