# Whisper App

OpenAI Whisper voice recording application with system tray GUI and GPU acceleration.

## Features

- 🎤 Real-time audio recording with visual feedback
- 🤖 GPU-accelerated transcription using OpenAI Whisper
- 🖥️ System tray integration for KDE/Wayland
- 📝 Transcription history management
- ✨ Optional Claude AI processing for text cleanup
- ⚙️ Microphone configuration via GUI
- 🔒 Singleton pattern (prevents multiple instances)
- 🐛 Comprehensive debug logging

## Project Structure

```
whisper/
├── src/
│   └── whisper_app/
│       ├── __init__.py          # Package initialization
│       ├── cli.py               # WhisperCLI (audio recording & transcription)
│       ├── gui.py               # WhisperGUI (PyQt6 interface)
│       └── __main__.py          # Entry point for package execution
├── tests/
│   ├── __init__.py
│   ├── test_gui.py              # Unit tests for GUI with mocks
│   └── test_cli.py              # Unit tests for CLI with mocks
├── pyproject.toml               # Package configuration (PEP 517/518)
├── setup.py                     # Backward compatible setup
├── requirements.txt             # Dependencies
└── README.md                    # This file
```

## Installation

### Prerequisites

- Python 3.8 or higher
- CUDA-capable GPU (optional, falls back to CPU)
- ffmpeg (required for audio processing)
- PortAudio (for PyAudio)

### System Dependencies (Debian/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg portaudio19-dev python3-dev
```

### Install Package

#### Development Installation (Editable)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in editable mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

#### Production Installation

```bash
pip install .
```

## Usage

### Running the GUI

```bash
# If installed via pip
whisper-gui

# Or run as module
python -m whisper_app

# Or from source
cd /path/to/whisper
source venv/bin/activate
python -m whisper_app
```

### Running as Systemd Service

The application runs automatically on login via systemd user service.

```bash
# Enable service
systemctl --user enable whisper-gui.service

# Start service
systemctl --user start whisper-gui.service

# Check status
systemctl --user status whisper-gui.service

# View logs
journalctl --user -u whisper-gui.service -f
```

### Configuration

Configuration is stored in `~/.whisper/`:
- `config` - Microphone device selection
- `history.json` - Transcription history
- `app.lock` - Singleton lock file

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=whisper_app --cov-report=html

# Run specific test file
pytest tests/test_gui.py

# Run specific test class
pytest tests/test_gui.py::TestWhisperGUIInitialization

# Run specific test
pytest tests/test_gui.py::TestWhisperGUIInitialization::test_gui_initialization
```

### Code Quality

```bash
# Format code with black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Lint with flake8
flake8 src/ tests/

# Type check with mypy
mypy src/
```

### Project Structure Guidelines

- **src layout**: Modern Python package structure (PEP 420)
- **Tests**: Comprehensive unit tests with mocks for all components
- **Type hints**: Optional but recommended for public APIs
- **Documentation**: Docstrings for all public classes and methods

## Architecture

### CLI Module (`cli.py`)

- **WhisperCLI**: Core audio recording and transcription logic
- CUDA detection and device selection
- PyAudio stream management
- Whisper model integration
- Audio buffer handling
- Configuration management

### GUI Module (`gui.py`)

- **WhisperGUI**: Main PyQt6 application window
- **RecordingThread**: Asynchronous recording worker
- **CodexWorker**: Claude AI integration for text processing
- System tray integration
- History management
- Settings dialog

### Key Design Patterns

- **Singleton**: Prevents multiple instances via file locking
- **Threading**: Separate threads for recording and transcription
- **Signal/Slot**: PyQt6 signal/slot for async communication
- **Dependency Injection**: Mocked dependencies in tests

## GPU Acceleration

The application automatically detects CUDA availability:

```python
device = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model("medium", device=device)
```

To verify GPU usage:

```bash
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

## Troubleshooting

### No Audio Data Recorded

- Check microphone selection in settings (⚙️ button)
- Verify microphone permissions
- Check `journalctl --user -u whisper-gui.service` for errors

### ffmpeg Not Found

The systemd service PATH must include system directories:

```ini
Environment="PATH=/path/to/venv/bin:/usr/local/bin:/usr/bin:/bin"
```

### CUDA Out of Memory

Switch to smaller model in `src/whisper_app/cli.py`:

```python
self.model = whisper.load_model("base", device=self.device)  # Instead of "medium"
```

### Multiple Instances Running

The singleton pattern prevents this, but if needed:

```bash
rm ~/.whisper/app.lock
systemctl --user restart whisper-gui.service
```

## Testing

The test suite uses extensive mocking to avoid dependencies on:
- Audio hardware
- GPU/CUDA
- PyQt6 GUI components
- OpenAI Whisper models

All external dependencies are mocked for fast, reliable testing.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass: `pytest`
5. Format code: `black src/ tests/`
6. Submit pull request

## License

MIT License

## Author

Rahul Rajaram (rahulrajaram2005@gmail.com)

## Acknowledgments

- OpenAI Whisper for speech recognition
- PyQt6 for GUI framework
- PyAudio for audio capture
