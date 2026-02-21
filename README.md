# Whisper GUI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/downloads/)
[![CUDA Support](https://img.shields.io/badge/CUDA-12.9-green)](https://developer.nvidia.com/cuda-toolkit)

A sleek PyQt6 desktop application for real-time speech-to-text transcription with GPU acceleration, system tray integration, and AI-powered text processing.

## Features

🎤 **Speech-to-Text Transcription**
- Real-time transcription using OpenAI's Whisper model
- GPU acceleration (CUDA) for fast processing
- CPU fallback for systems without NVIDIA GPU

🧠 **AI Text Processing**
- Claude integration for intelligent text refinement
- Automatic keyword highlighting
- Typo correction and grammar improvement

📊 **User-Friendly GUI**
- PyQt6 desktop application with system tray integration
- Clean interface for recording and managing transcriptions
- Real-time transcription history with timestamps
- Click-to-copy functionality for quick workflow

⚙️ **Advanced Features**
- Microphone device selection and configuration
- Persistent history storage
- System tray icon with status indicators
- Automatic startup via systemd user service
- Multi-architecture IPC (Inter-Process Communication)
- Cross-desktop compatibility (KDE, GNOME, Wayland)

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager
- PyAudio system library
- (Optional) NVIDIA GPU with CUDA support for faster transcription

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/whisper-gui.git
cd whisper-gui
```

#### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

For **development**, also install dev dependencies:

```bash
pip install -e ".[dev]"
```

#### 4. Run the Application

```bash
python -m whisper_app
```

Or use the entry point:

```bash
whisper-gui
```

### System Tray Setup (Linux/KDE)

For automatic startup and system tray integration:

```bash
./scripts/setup_venv_systemd.sh
```

This will:
- Set up systemd user services
- Configure desktop shortcuts
- Enable automatic startup on login

## Usage

### Recording

1. **Start Recording**: Click the ▶ button (or use keyboard shortcut if configured)
2. **Speak**: Your voice is recorded and processed by Whisper
3. **Stop Recording**: Click the ⏹ button
4. **View Result**: Transcription appears in history list

### Text Processing with Claude

1. **Select Text**: Click any transcription in the history
2. **Process**: Click the ✨ button to enhance with Claude
3. **View Result**: Keywords are highlighted, typos are fixed
4. **Copy**: Click to copy to clipboard

### Keyboard Shortcuts

- **Hotkey Recording** (Configurable): Triple-Ctrl to toggle recording
- **Copy to Clipboard**: Click any result to copy

## Architecture

```
whisper-gui/
├── src/whisper_app/           # Main source code
│   ├── gui.py                 # PyQt6 GUI implementation
│   ├── cli.py                 # Whisper engine and recording logic
│   ├── ipc_controller.py      # Inter-process communication base
│   ├── fifo_controller.py     # FIFO-based IPC for hotkey events
│   └── dbus_controller.py     # D-Bus IPC alternative
├── config/
│   ├── systemd/               # Systemd service files
│   └── desktop/               # Desktop shortcuts
├── scripts/                   # Setup and utility scripts
├── docs/                      # Comprehensive documentation
├── tests/                     # Test suite
├── requirements.txt           # Python dependencies (pinned versions)
└── pyproject.toml            # Project metadata and build config
```

### Key Components

**gui.py** - PyQt6 desktop interface with:
- Main window with recording controls
- History table with transcriptions
- System tray integration
- Thread workers for non-blocking operations

**cli.py** - Whisper engine with:
- Audio recording using PyAudio
- Whisper model inference (CPU/GPU)
- Audio configuration management
- Microphone device selection

**ipc_controller.py** - Communication between processes:
- Base class for inter-process messaging
- Supports hotkey daemon communication
- Clean abstraction for different IPC methods

**fifo_controller.py** - FIFO-based IPC:
- Reliable message passing for hotkey events
- Wayland-compatible (doesn't rely on X11)
- Graceful error handling

## Configuration

### Microphone Selection

On first run, you'll be prompted to select your microphone. To reconfigure:

```bash
rm ~/.whisper/config
python -m whisper_app
```

### GPU/CUDA Setup

The app automatically detects CUDA availability. To verify:

```bash
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

For CUDA installation, see [CUDA Installation Guide](https://developer.nvidia.com/cuda-downloads).

### Whisper Model

The app uses the "medium" Whisper model by default. To use a different model, modify `cli.py:34`:

```python
self.model = whisper.load_model("base", device=self.device)  # Options: tiny, base, small, medium, large
```

## Troubleshooting

### Application Won't Start

**Check service status:**
```bash
systemctl --user status whisper-gui
journalctl --user -u whisper-gui -n 50
```

**Check for missing dependencies:**
```bash
pip install -r requirements.txt
```

**Issue**: `ModuleNotFoundError: No module named 'pyaudio'`
- **Solution**: Install system audio libraries
  - Ubuntu/Debian: `sudo apt-get install python3-dev portaudio19-dev`
  - Fedora: `sudo dnf install python3-devel portaudio-devel`
  - macOS: `brew install portaudio`

### Transcription is Slow

**Cause**: Model is running on CPU instead of GPU
**Solution**: Verify CUDA setup
```bash
python3 -c "import torch; print('CUDA:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name() if torch.cuda.is_available() else 'CPU')"
```

If CUDA is available but not being used, check NVIDIA driver:
```bash
nvidia-smi
```

**Workaround**: Use smaller Whisper model (change "medium" to "base" or "small" in cli.py)

### Tray Icon Not Showing

**Cause**: KDE/GNOME doesn't display all tray icons by default

**Solutions**:
1. Check tray icon settings in your desktop environment
2. Try pinning the icon to your taskbar
3. Verify the application is running: `ps aux | grep whisper_app`

### Audio Device Not Detected

**Check available devices:**
```bash
python3 << 'EOF'
import pyaudio
audio = pyaudio.PyAudio()
for i in range(audio.get_device_count()):
    info = audio.get_device_info_by_index(i)
    print(f"{i}: {info['name']} (inputs: {info['maxInputChannels']})")
EOF
```

**Reconfigure microphone:**
```bash
rm ~/.whisper/config
python -m whisper_app
```

### Recording Stops Unexpectedly

**Check journalctl for errors:**
```bash
journalctl --user -u whisper-gui -f
```

**Common causes**:
- Microphone disconnected
- Audio buffer overflow (lower audio quality in pyaudio settings)
- Thread timeout in transcription (increase timeout in gui.py:112)

**Solution**: Restart the service
```bash
systemctl --user restart whisper-gui
```

### Claude Processing Fails

**Check if Claude CLI is installed:**
```bash
which claude
```

**Setup Claude CLI:**
```bash
npm install -g claude
claude setup-token  # Enter your API key
```

**Verify connection:**
```bash
echo "Hello" | claude --print
```

### High Memory Usage

**Cause**: Whisper model loaded in memory (normal, ~5GB for "medium" model)

**Solution**: Use smaller model or reduce history size
- Edit history limit in gui.py if needed
- Consider using "base" or "small" model for limited-RAM systems

### Permission Denied Errors

**Check file permissions:**
```bash
ls -la ~/.whisper/
ls -la ~/.config/systemd/user/
```

**Fix permissions:**
```bash
mkdir -p ~/.whisper ~/.config/systemd/user
chmod 755 ~/.whisper ~/.config/systemd/user
```

## Development

### Setting Up Development Environment

```bash
# Clone and install with dev dependencies
git clone https://github.com/yourusername/whisper-gui.git
cd whisper-gui
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest --cov=whisper_app       # With coverage report
pytest tests/test_hotkey.py    # Run specific test file
```

### Code Style and Linting

```bash
# Format code with black
black src/ tests/

# Check code style
flake8 src/ tests/

# Type checking
mypy src/

# Import sorting
isort src/ tests/
```

### Making Changes

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Run tests: `pytest`
4. Run linter: `black . && flake8 . && mypy src/`
5. Commit: `git commit -m "Feature: description"`
6. Push: `git push origin feature/my-feature`
7. Open a Pull Request

## System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| Python | 3.8 | 3.11+ |
| RAM | 4GB | 8GB+ |
| VRAM (GPU) | - | 4GB+ |
| Disk | 2GB | 5GB+ |
| OS | Linux | Ubuntu 20.04+, Fedora, KDE Neon |

### Dependencies

All Python dependencies are specified in `requirements.txt` with pinned versions for reproducibility.

Core packages:
- **openai-whisper**: Speech-to-text engine
- **PyQt6**: Desktop GUI framework
- **torch**: Deep learning framework (with CUDA support)
- **pyaudio**: Audio recording
- **pynput**: Keyboard input handling

## Platform Support

- ✅ **Linux** (Primary - tested on Debian/Ubuntu, Fedora)
- ⚠️ **macOS** (Partial - audio may require system audio frameworks)
- ❌ **Windows** (Not tested - may require modifications)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Follow code style guidelines (see above)
5. Submit a Pull Request

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for detailed guidelines.

## Documentation

- **[Quick Start](docs/QUICK_START.md)** - Get up and running in 5 minutes
- **[Architecture](docs/MULTI_OS_ARCHITECTURE.md)** - System design and components
- **[Hotkey Setup](docs/HOTKEY_DAEMON_README.md)** - Configure keyboard shortcuts
- **[GUI Guide](docs/WHISPER_GUI_README.md)** - Full feature documentation
- **[Systemd Setup](docs/VENV_SYSTEMD_SETUP.md)** - Service configuration details

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Author

**Rahul Rajaram**
- Email: rahulrajaram2005@gmail.com
- GitHub: [@rahulrajaram](https://github.com/rahulrajaram)

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech-to-text engine
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework
- [Claude](https://claude.ai/) - AI text processing
- [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) - Audio recording

## Roadmap

- [ ] Multi-language support
- [ ] Custom hotkey configuration UI
- [ ] Export transcriptions (PDF, Word)
- [ ] Batch transcription from audio files
- [ ] Local LLM integration (Ollama)
- [ ] Cloud storage integration
- [ ] Browser extension for webpage transcription
- [ ] Real-time transcription captions

## Support

For issues, questions, or suggestions:
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/yourusername/whisper-gui/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/whisper-gui/discussions)
- 📧 **Email**: rahulrajaram2005@gmail.com

## Project Status

**Status**: Active Development (Beta)

The project is actively maintained. Major features are stable, but expect occasional updates and improvements.

---

**Last Updated**: November 2025
