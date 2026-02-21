# Whisper GUI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Linux Only](https://img.shields.io/badge/Platform-Linux-lightgrey)](https://kernel.org)

A PyQt6 desktop application for speech-to-text transcription using [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (large-v3) with GPU acceleration, system tray integration, and systemd autostart.

> **Platform: Linux only.** This application depends on systemd, FIFO-based IPC, PyAudio/ALSA, and X11/XCB. It does not work on macOS or Windows.

## Features

- **Speech-to-text** using faster-whisper large-v3 (best Whisper model, 4-6x faster than openai-whisper via CTranslate2)
- **GPU acceleration** with CUDA float16 (~4 GB VRAM), automatic CPU fallback with int8 quantization
- **PyQt6 GUI** with system tray icon, recording controls, transcription history, and click-to-copy
- **Systemd integration** for autostart on login
- **Keyboard shortcut** via FIFO IPC — bind any desktop shortcut to toggle recording (Wayland-compatible)
- **Claude integration** for AI-powered text refinement and keyword highlighting

## Requirements

| | Minimum | Recommended |
|---|---|---|
| OS | Linux (Debian/Ubuntu, Fedora, Arch) | Debian 12+, Ubuntu 22.04+ |
| Python | 3.8 | 3.11+ |
| RAM | 4 GB | 8 GB+ |
| VRAM (GPU) | 4 GB (NVIDIA) | 6 GB+ |
| Disk | 5 GB (model download) | 10 GB |

System packages needed:

```bash
# Debian/Ubuntu
sudo apt install python3-dev portaudio19-dev

# Fedora
sudo dnf install python3-devel portaudio-devel
```

## Installation

```bash
git clone https://github.com/rahulrajaram/whisper-app.git
cd whisper-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

The first run will download the large-v3 model (~3 GB) from HuggingFace. This happens once.

### Quick test

```bash
source venv/bin/activate
python -m whisper_app
```

## Systemd Setup (Recommended)

The setup script creates a virtual environment, installs dependencies, and configures a systemd user service that starts the GUI on login.

```bash
./scripts/setup_venv_systemd.sh
```

Then start it immediately:

```bash
systemctl --user start whisper-gui
```

### Managing the service

```bash
systemctl --user status whisper-gui     # Check status
journalctl --user -u whisper-gui -f     # View logs
systemctl --user restart whisper-gui    # Restart after code changes
systemctl --user stop whisper-gui       # Stop
systemctl --user disable whisper-gui    # Disable autostart
```

## Keyboard Shortcut Setup

Recording is controlled via the `whisper-recording-toggle` script, which communicates with the running GUI through a FIFO pipe. This approach works on both X11 and Wayland.

### KDE Plasma

1. Open **System Settings > Shortcuts > Custom Shortcuts**
2. Add a new **Global Shortcut > Command/URL**
3. Set the trigger to your preferred key combo (e.g. `Ctrl+Alt+Shift+R`)
4. Set the command to:
   ```
   /path/to/whisper-app/scripts/whisper-recording-toggle toggle
   ```

### GNOME

```bash
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings \
  "['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/whisper/']"

gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/whisper/ \
  name 'Whisper Toggle' \
  command '/path/to/whisper-app/scripts/whisper-recording-toggle toggle' \
  binding '<Ctrl><Alt><Shift>r'
```

### Other desktops

Any mechanism that can run a shell command on a keypress will work. Point it at:

```
/path/to/whisper-app/scripts/whisper-recording-toggle toggle
```

The toggle script also supports `start`, `stop`, and `status` subcommands.

## Usage

1. **Start recording**: Press your keyboard shortcut or click the record button in the GUI
2. **Speak**: Audio is captured via your selected microphone
3. **Stop recording**: Press the shortcut again or click stop
4. **View result**: Transcription appears in the history table — click any row to copy to clipboard

### Microphone selection

On first run you will be prompted to select a microphone. To reconfigure later:

```bash
rm ~/.whisper/config
systemctl --user restart whisper-gui
```

## Architecture

```
whisper-app/
├── src/whisper_app/
│   ├── gui/                  # PyQt6 GUI (main_window, presenter, history, workers)
│   ├── cli.py                # Headless CLI mode
│   ├── config.py             # Runtime configuration (model, device, hotkeys)
│   ├── controllers/          # Recording controller (start/stop/toggle)
│   ├── services/             # TranscriptionService (faster-whisper), AudioInput, RecordingSession
│   ├── hotkeys/              # Pynput-based hotkey backend (disabled by default)
│   ├── fifo_controller.py    # FIFO-based IPC for external shortcut commands
│   ├── dbus_controller.py    # D-Bus IPC (with FIFO fallback)
│   └── command_bus.py        # Command dispatch (toggle/start/stop)
├── config/systemd/           # Service file template
├── scripts/
│   ├── setup_venv_systemd.sh # One-command setup
│   └── whisper-recording-toggle  # CLI to control recording via FIFO
└── tests/                    # Test suite (pytest)
```

### How recording control works

```
KDE/GNOME shortcut
  -> whisper-recording-toggle toggle
    -> writes "toggle" to ~/.whisper/control.fifo
      -> FifoController reads it
        -> CommandBus dispatches to GUI
          -> start or stop recording
```

## GPU / CUDA

The app auto-detects CUDA. To verify:

```bash
python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"
nvidia-smi  # Should show ~4 GB used when model is loaded
```

If CUDA is unavailable, the app falls back to CPU with int8 quantization (slower but functional).

## Limitations

- **Linux only** — depends on systemd, FIFO IPC, ALSA/PulseAudio, and X11/XCB. No macOS or Windows support.
- **NVIDIA GPU recommended** — CPU inference works but is significantly slower (~10-30x for large-v3).
- **First startup is slow** — the large-v3 model (~3 GB) must be downloaded once from HuggingFace, and loading it into GPU memory takes 30-60 seconds on each start.
- **Single instance** — only one GUI process should run at a time (enforced via `~/.whisper/app.lock`).

## Troubleshooting

**Service won't start:**
```bash
journalctl --user -u whisper-gui -n 50
# Common: ModuleNotFoundError — run ./scripts/setup_venv_systemd.sh again
```

**No audio input detected:**
```bash
python3 -c "
import pyaudio
audio = pyaudio.PyAudio()
for i in range(audio.get_device_count()):
    info = audio.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        print(f'{i}: {info[\"name\"]}')
"
# Then: rm ~/.whisper/config && systemctl --user restart whisper-gui
```

**Shortcut triggers twice:**
Make sure you only have one mechanism bound — either a desktop shortcut calling `whisper-recording-toggle`, or the built-in pynput hotkey (disabled by default), but not both.

**High memory usage:**
~4 GB VRAM for the model is expected. System RAM usage is typically 1-2 GB.

## Development

```bash
pip install -e ".[dev]"
pytest                        # Run all tests
pytest -v --cov=whisper_app   # With coverage
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Author

Rahul Rajaram — [GitHub](https://github.com/rahulrajaram)
