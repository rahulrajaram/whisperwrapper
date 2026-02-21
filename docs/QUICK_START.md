# Whisper GUI - Quick Start Guide

## What You Have

A complete voice recording application with:
- 🎤 Speech-to-text recording (OpenAI Whisper)
- 💬 AI text processing with Claude
- 📝 History with bold keyword highlighting
- 🎯 System tray integration (appears in KDE panel)
- 🚀 Automatic startup on login
- 🐍 Isolated Python environment (no system dependencies)

## First-Time Setup

```bash
cd ~/Documents/whisper
./setup_venv_systemd.sh
```

Then **log out and log back in** - app starts automatically! 🎉

## Using Whisper

### From System Tray
1. Look for **🎤 microphone icon** in bottom-right panel
2. Right-click for menu options
3. Double-click to show/hide window

### Recording
1. Click **▶ Start Recording** (green button)
2. Speak into microphone
3. Click **⏹ Stop Recording** (red button)
4. Text appears in history (newest first)

### Processing with Claude
1. Click a transcription row to select it
2. Click **✨ Process with Claude** (purple button)
3. Keywords get highlighted with **bold** formatting
4. Typos are fixed automatically
5. Result replaces original text and copies to clipboard

### Other Features
- **🗑 Clear History** (orange) - Remove all transcriptions
- **🔒/🔓 Lock** - Protect items from bulk deletion
- **Copy** - Copy any transcription to clipboard
- **💻 Terminal** (blue) - Open terminal in project folder

## Quick Commands

```bash
# Check status
systemctl --user status whisper-gui

# View logs
journalctl --user -u whisper-gui -f

# Start/stop (if not auto-started)
systemctl --user start whisper-gui
systemctl --user stop whisper-gui

# Edit in terminal
cd ~/Documents/whisper
source venv/bin/activate
nano whisper_gui.py
```

## File Structure

```
~/Documents/whisper/
├── whisper_gui.py           ← Main GUI application
├── whisper_cli.py           ← Recording engine
├── venv/                    ← Isolated Python (auto-created)
├── requirements.txt         ← Dependencies list
├── VENV_SYSTEMD_SETUP.md    ← Detailed venv documentation
├── SYSTEM_TRAY_SETUP.md     ← System tray guide
└── QUICK_START.md           ← This file
```

## Troubleshooting

### App not starting on login?
```bash
systemctl --user status whisper-gui
journalctl --user -u whisper-gui
```

### Want to reinstall venv?
```bash
cd ~/Documents/whisper
rm -rf venv/
./setup_venv_systemd.sh
```

### Need to disable autostart?
```bash
systemctl --user disable whisper-gui
```

To re-enable:
```bash
systemctl --user enable whisper-gui
```

## Documentation

- **VENV_SYSTEMD_SETUP.md** - Detailed setup and virtual environment guide
- **SYSTEM_TRAY_SETUP.md** - System tray and KDE integration documentation
- **WHISPER_GUI_README.md** - Full feature documentation

## That's It! 🚀

Your Whisper voice recording app is ready to use:
- ✅ Starts automatically on login
- ✅ Accessible from system tray
- ✅ AI-powered text processing
- ✅ Isolated Python environment
- ✅ Full keyboard/mouse support

Just use it! No manual startup needed.
