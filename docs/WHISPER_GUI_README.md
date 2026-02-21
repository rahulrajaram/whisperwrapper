# Whisper GUI - Voice Recording Application

A minimal PyQt6 desktop application for recording and transcribing speech using OpenAI's Whisper model.

## Features

✅ **Start/Stop Recording** - Simple buttons to control voice recording
✅ **Transcription History** - Scrollable table with all past transcriptions
✅ **Copy to Clipboard** - Click a row to copy transcription to clipboard
✅ **Persistent History** - All recordings are saved to `~/.whisper/gui_history.json`
✅ **Native Desktop App** - Runs as a proper Linux PyQt6 application

## Installation

### 1. Install Dependencies

```bash
# Install system dependencies for PyQt6
sudo apt-get update
sudo apt-get install -y python3-pyqt6

# Or install via pip
pip install PyQt6
```

The application also requires the base Whisper dependencies which should already be installed:
```bash
pip install -r requirements.txt
```

### 2. Verify Installation

```bash
cd ~/Documents/whisper
python3 -c "from PyQt6.QtWidgets import QApplication; print('✅ PyQt6 installed')"
```

## Usage

### Run the Application

```bash
cd ~/Documents/whisper
python3 whisper_gui.py
```

Or directly:
```bash
~/Documents/whisper/whisper_gui.py
```

### Using the GUI

1. **Start Recording**: Click the green "▶ Start Recording" button
   - The button will disable and "⏹ Stop Recording" becomes active
   - Status shows "🎤 Recording... (Press Stop when done)"

2. **Speak**: Speak into your microphone at normal volume
   - Recording continues until you click Stop

3. **Stop Recording**: Click the red "⏹ Stop Recording" button
   - Status shows "⏳ Processing transcription..."
   - Whisper AI processes your audio and transcribes it
   - **Transcription is automatically copied to clipboard** ✅
   - Status shows "✅ Transcription copied to clipboard"

4. **Paste Transcription**:
   - Your transcription is already in the clipboard
   - Paste it with Ctrl+V in any application
   - Email, chat, text editor, anywhere!

5. **View History**:
   - All transcriptions appear in the table at the bottom
   - Newest recordings appear first
   - Table shows timestamp, full transcription, and copy button

6. **Copy from History**:
   - Click the "Copy" button in any row to copy that transcription again
   - Status bar confirms: "✅ Copied to clipboard..."
   - Paste with Ctrl+V in any application

7. **Clear History**:
   - Click the orange "🗑 Clear History" button
   - All transcriptions are removed
   - History file is updated

## History Storage

Transcriptions are saved to: `~/.whisper/gui_history.json`

Example format:
```json
[
  {
    "timestamp": "2025-11-01 14:30:45",
    "text": "Hello world this is a test"
  },
  {
    "timestamp": "2025-11-01 14:25:12",
    "text": "Another recording"
  }
]
```

You can manually back up this file or access it programmatically.

## Requirements

- **Python 3.7+**
- **PyQt6** - GUI framework
- **openai-whisper** - Speech-to-text model
- **pyaudio** - Audio input
- **Microphone** - Any working input device

## Troubleshooting

### PyQt6 Not Installed
```bash
pip install PyQt6
# Or
sudo apt-get install python3-pyqt6
```

### No Microphone Detected
1. Check your microphone is connected
2. Test with: `python3 whisper_cli.py --configure`
3. The GUI uses the same microphone configuration

### Recording Produces No Audio
- Make sure your microphone is not muted
- Test volume levels: `alsamixer` or `pavucontrol`
- Check microphone permissions (should be accessible to your user)

### Clipboard Not Working
The GUI supports both X11 and Wayland:
- **X11**: Uses `xclip` (usually installed)
- **Wayland**: Uses `wl-copy` (included in most Wayland desktops)

Install if missing:
```bash
# For X11
sudo apt-get install xclip

# For Wayland
sudo apt-get install wl-clipboard
```

### Whisper Model Not Downloading
First run may download the model (~1.4GB). This is normal.
```bash
# Pre-download to speed up first GUI start
python3 -c "import whisper; whisper.load_model('base')"
```

## Integration with Hotkey Daemon

This GUI app is standalone, but you can also use it alongside the hotkey daemon:

1. **Run hotkey daemon** in one terminal:
   ```bash
   sudo ./run_daemon.sh --debug
   ```

2. **Run GUI** in another terminal:
   ```bash
   ./whisper_gui.py
   ```

Both can run simultaneously. Use the GUI for manual recording and hotkeys for quick voice input from anywhere.

## Application Architecture

```
whisper_gui.py (Main GUI window)
├── WhisperGUI (QMainWindow)
│   ├── start_recording() - Initiates recording
│   ├── stop_recording() - Stops recording and triggers transcription
│   └── copy_to_clipboard() - Copies history items
│
├── RecordingWorker (QObject in separate thread)
│   ├── run() - Handles recording/transcription process
│   ├── result - Signal emits transcription text
│   └── error - Signal emits error messages
│
└── whisper_cli.WhisperCLI
    ├── start_recording() - Begins audio capture
    ├── stop_recording() - Processes audio to transcription
    └── cleanup() - Closes audio resources
```

## Development Notes

### Adding Custom Features

To customize the GUI, edit `whisper_gui.py`:

- **Change button colors**: Modify `setStyleSheet()` calls in `setup_ui()`
- **Adjust history size**: Modify `self.history` list
- **Change transcription model**: Modify `WhisperCLI` initialization
- **Add new columns**: Modify `history_table` setup and `refresh_history_table()`

### Running in Debug Mode

```bash
python3 -u whisper_gui.py 2>&1 | tee gui.log
```

## License

Same as parent Whisper project

## Support

For issues with:
- **GUI**: Edit `whisper_gui.py`
- **Recording**: Check `whisper_cli.py`
- **Hotkeys**: See `HOTKEY_DAEMON_README.md`
