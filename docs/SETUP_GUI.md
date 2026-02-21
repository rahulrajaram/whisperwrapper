# Whisper GUI - Quick Setup Guide

## 1. Install PyQt6

```bash
pip install PyQt6
```

Or system-wide:
```bash
sudo apt-get install python3-pyqt6
```

## 2. Run the Application

From the whisper directory:

```bash
# Option 1: Run launcher script
./launch_gui.sh

# Option 2: Run directly
python3 whisper_gui.py

# Option 3: Run with absolute path
~/Documents/whisper/whisper_gui.py
```

## 3. Launch from Application Menu (Optional)

The desktop entry has been installed. You can now:
- Click Applications → Find "Whisper Voice Recording"
- Or press Super key and type "Whisper"
- Click to launch the GUI

## File Structure

```
~/Documents/whisper/
├── whisper_gui.py           # Main GUI application
├── launch_gui.sh            # Launcher script
├── whisper-gui.desktop      # Desktop entry for app menu
├── whisper_cli.py           # Core recording/transcription logic
├── WHISPER_GUI_README.md    # Full documentation
├── SETUP_GUI.md            # This file
└── requirements.txt         # Python dependencies
```

## First Run

On first run, Whisper will download the base model (~1.4GB). This is normal and only happens once.

Progress will be shown in the terminal. Subsequent runs will be instant.

## Microphone Configuration

The GUI uses the same microphone configuration as `whisper_cli.py`.

If you need to change microphones:
```bash
python3 whisper_cli.py --configure
```

## Features

- ▶️ **Start/Stop**: Simple buttons to control recording
- 📝 **History**: See all past transcriptions
- 📋 **Copy**: Click any row to copy to clipboard
- 💾 **Persistent**: All history saved to `~/.whisper/gui_history.json`
- 🎯 **Native**: Proper PyQt6 Linux desktop application

## Troubleshooting

### "No module named 'PyQt6'"
Install PyQt6:
```bash
pip install PyQt6
```

### "No microphone found"
1. Check connection: `python3 whisper_cli.py --configure`
2. Check volume: `alsamixer`
3. Check permissions: Should work as your user

### "Copy to clipboard not working"
For Wayland (Plasma):
```bash
sudo apt-get install wl-clipboard
```

For X11 (XFCE):
```bash
sudo apt-get install xclip
```

## Next Steps

- **Learn Features**: See `WHISPER_GUI_README.md` for full documentation
- **Use Hotkeys**: The GUI ships with a built-in listener (Ctrl+Alt+Shift+R) or configure desktop shortcuts via `SHORTCUT_SETUP.md`
- **Integrate**: Use with other applications or build on the codebase

Enjoy! 🎤✨
