# Whisper CLI and Process Architecture Analysis

## Project Overview

The Whisper project is a speech-to-text system with multiple interface layers that can identify, communicate with, and integrate into different CLI instances (Claude CLI, Codex CLI, or other REPL environments).

**Location:** `/home/rahul/Documents/whisper/`

---

## CLI Architecture Components

### 1. Core Components

#### **whisper_cli.py** - Primary Speech-to-Text Engine
- **Purpose:** Central module providing speech recording and transcription functionality
- **Key Classes:** `WhisperCLI`
- **Features:**
  - Headless mode operation (`--headless` flag)
  - Debug mode support (`--debug` flag)
  - Configuration management via `~/.whisper/config`
  - Multiple execution modes (interactive REPL or single operation)

#### **whisper** - Shell Wrapper Script
- **Purpose:** Clean entry point that suppresses ALSA/JACK audio warnings
- **Operation:** Redirects stderr to `/dev/null` and calls `whisper_cli.py`

#### **whisper_gui.py** - PyQt6 GUI Application
- **Purpose:** Graphical interface with process integration capabilities
- **Key Features:**
  - Process discovery and selection
  - Direct stdin communication with child processes
  - History tracking and clipboard management
  - Real-time process monitoring

#### **whisper_hotkey_daemon.py** - Global Hotkey Listener
- **Purpose:** Background daemon monitoring for CTRL+ALT+R hotkey
- **Execution:** Runs as a system service with elevated privileges
- **Features:**
  - Keyboard event monitoring via `/dev/input/event*`
  - Wayland/X11 compatibility
  - Clipboard integration

---

## Process Identification & Discovery

### How the System Identifies Different CLI Processes

The GUI application (`whisper_gui.py`) includes sophisticated process discovery capabilities:

```python
def refresh_cli_processes(self):
    """Discover running Claude/Codex CLI processes"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        cmdline_str = ' '.join(proc.info['cmdline'])
        if 'claude' in cmdline_str.lower() or 'codex' in cmdline_str.lower():
            # Store as: {display_name: (pid, process_object)}
            display_name = f"{cmd_name} (PID: {proc.pid})"
            self.available_processes[display_name] = (proc.pid, proc)
```

**Identification Mechanisms:**

1. **Command-line Scanning:** Uses `psutil.process_iter()` to scan all running processes
2. **Keyword Matching:** Searches process cmdline for strings: `'claude'` or `'codex'` (case-insensitive)
3. **PID Tracking:** Stores Process ID for each discovered instance
4. **Process Object Reference:** Maintains the actual process object for live communication

### Process Selection Metadata

Each discovered process is displayed as:
```
<command_name> (PID: <process_id>)
```

Example:
- `claude (PID: 12345)`
- `codex (PID: 12346)`
- `python3 (PID: 12347)` (if running from Python directly)

---

## Communication Channels

### 1. Direct stdin Communication (Via `/proc/[pid]/fd/0`)

The GUI can write transcribed text directly to a selected process's stdin:

```python
def write_to_process_stdin(self, text: str) -> bool:
    """
    Write text to selected process's stdin.
    Uses /proc/[pid]/fd/0 to write directly to the process's stdin file descriptor.
    """
    stdin_path = f"/proc/{self.selected_process_pid}/fd/0"
    if os.path.exists(stdin_path):
        with open(stdin_path, 'w') as stdin_fd:
            stdin_fd.write(text + '\n')
            stdin_fd.flush()
        return True
```

**How it works:**
- Opens `/proc/[pid]/fd/0` (process's stdin file descriptor)
- Writes transcribed text directly to process's input stream
- Process receives text as if user typed it
- Appends newline for REPL processing

### 2. Clipboard Communication

When no specific process is selected:
```python
# Clipboard write via subprocess
subprocess.run(['wl-copy'], input=text.encode(), check=True)  # Wayland
# OR
subprocess.run(['xclip', '-selection', 'clipboard'], input=text)  # X11
```

### 3. Named Pipe (FIFO) Communication

For headless mode, supports optional FIFO writing:
```python
def _write_to_fifo(self, transcript):
    fifo_path = os.environ.get('WHISPER_TRANSCRIPT_FIFO')
    # Write to FIFO if environment variable is set
```

**Environment Variable:** `WHISPER_TRANSCRIPT_FIFO`

---

## Environment Variables & Configuration

### System Environment Variables

1. **Display Variables** (Detection of graphical session)
   - `DISPLAY` - X11 display socket
   - `WAYLAND_DISPLAY` - Wayland display identifier
   - `XDG_VTNR` - Virtual terminal number

2. **Audio Configuration** (Set by WhisperCLI during init)
   - `ALSA_PCM_CARD=default` - ALSA sound card
   - `ALSA_PCM_DEVICE=0` - ALSA device
   - `JACK_NO_AUDIO_RESERVATION=1` - JACK audio system suppression
   - `PULSE_LATENCY_MSEC=30` - PulseAudio latency settings

3. **FIFO Communication** (Optional)
   - `WHISPER_TRANSCRIPT_FIFO` - Path to named pipe for headless output

### User Configuration Files

1. **Microphone Configuration**
   - **Location:** `~/.whisper/config`
   - **Format:** JSON
   - **Content:**
     ```json
     {
       "input_device_index": 0
     }
     ```

2. **GUI History**
   - **Location:** `~/.whisper/gui_history.json`
   - **Format:** JSON with timestamps and transcriptions

3. **Claude Code Settings** (Project-specific)
   - **Location:** `.claude/settings.local.json`
   - **Purpose:** Stores permissions for Bash/Git operations

---

## Launch Methods & Execution Modes

### 1. Direct CLI Execution (Non-Interactive)

```bash
# Headless mode - single record/transcribe
python whisper_cli.py --headless

# With debug output
python whisper_cli.py --headless --debug

# Configuration mode
python whisper_cli.py --configure
```

**Return:** Outputs transcribed text to stdout or FIFO

### 2. Interactive CLI (REPL Mode)

```bash
# Full interactive loop
./whisper

# Interactive with debug
python whisper_cli.py --debug
```

**Input:** ENTER to start/stop recording

### 3. GUI Application

```bash
# Via launcher script
./launch_gui.sh

# Direct Python execution
python whisper_gui.py

# Via desktop application menu
# Uses .desktop entry at: whisper-gui.desktop
```

### 4. Hotkey Daemon (Background Service)

```bash
# Manual execution with debug
sudo ./run_daemon.sh --debug

# Systemd service (auto-startup)
systemctl --user enable whisper-hotkey
systemctl --user start whisper-hotkey
```

---

## Code Entry Points

### whisper_cli.py Main Entry Point

```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--configure', action='store_true')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    
    if args.configure:
        cli = WhisperCLI(headless=False, force_configure=True, debug=args.debug)
    else:
        cli = WhisperCLI(headless=args.headless, debug=args.debug)
        cli.run()

if __name__ == "__main__":
    main()
```

### whisper_gui.py Main Entry Point

```python
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = WhisperGUI()
    gui.show()
    sys.exit(app.exec())
```

### whisper_hotkey_daemon.py Main Entry Point

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    
    daemon = WhisperHotkeyDaemon(debug=args.debug)
    daemon.run()
```

---

## Process State & Control Flow

### WhisperCLI State Management

Key instance variables for tracking execution context:

```python
class WhisperCLI:
    def __init__(self, headless=False, force_configure=False, debug=False):
        self.headless = headless              # Execution mode flag
        self.debug = debug                    # Debug output flag
        self.recording = False                # Recording state
        self.audio_data = []                  # Audio buffer
        self.input_device_index = None        # Selected microphone
        self.config_file = "~/.whisper/config" # Config location
```

### Execution Paths

1. **Headless Path** (Single-use, for CLI integration)
   - Load model once
   - Record → Transcribe → Output to stdout/FIFO
   - Exit

2. **Interactive Path** (User-facing REPL)
   - Load model once
   - Loop: Wait for input → Record/Transcribe → Display → Continue
   - Exit on 'quit' command

3. **GUI Path** (Long-running process)
   - Load model once
   - QThread workers for non-blocking operations
   - Maintain history
   - Continuously scan for CLI processes
   - Flush transcriptions to clipboard and/or process stdin

---

## Integration Patterns

### Pattern 1: Function Import (In-Process)

```python
from whisper_recorder import handle_voice_command

# In REPL main loop
if user_input == '/voice':
    voice_text = handle_voice_command()
    if voice_text:
        user_input = voice_text  # Processed as normal input
```

### Pattern 2: Proxy Mode (Subprocess)

```python
# claude_integration.py acts as proxy
subprocess.Popen(['claude'], stdin=subprocess.PIPE)
# Intercepts /voice commands, manages subprocess I/O
```

### Pattern 3: GUI Selection (Out-of-Process)

```
User selects process in GUI dropdown
      ↓
GUI monitors for new recordings
      ↓
On transcription complete:
  - Write to /proc/[pid]/fd/0 (selected process stdin)
  - OR copy to clipboard
  - OR both
```

---

## Distinguishing Different Instances

### What Makes Each Process Unique

1. **Process ID (PID)**
   - Unique system identifier
   - Found via: `/proc/[pid]/cmdline`

2. **Command Line Arguments**
   - Different CLI tools (claude, codex, python script)
   - Detectable pattern: `'claude'` or `'codex'` in cmdline string

3. **File Descriptors**
   - Each process has unique stdin at `/proc/[pid]/fd/0`
   - Allows isolated text injection

4. **Environment Variables**
   - Each process has its own environment
   - `DISPLAY`, `WAYLAND_DISPLAY` indicate session type

5. **Parent Process**
   - Can identify shell or launcher script spawning the CLI

### Detection Order (in whisper_gui.py)

```python
# 1. Scan all processes
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    # 2. Get full command line
    cmdline_str = ' '.join(proc.info['cmdline'])
    
    # 3. Match against known patterns
    if 'claude' in cmdline_str.lower() or 'codex' in cmdline_str.lower():
        # 4. Store with identifying metadata
        display_name = f"{cmd_name} (PID: {proc.pid})"
        self.available_processes[display_name] = (proc.pid, proc)
```

---

## File Structure Summary

```
/home/rahul/Documents/whisper/
├── Core Modules
│   ├── whisper_cli.py              # Main speech-to-text engine
│   ├── whisper_recorder.py         # Reusable recorder module
│   └── whisper                     # Shell wrapper (no ALSA warnings)
│
├── GUI Application
│   ├── whisper_gui.py              # PyQt6 GUI with process integration
│   ├── launch_gui.sh               # GUI launcher with dependency check
│   └── whisper-gui.desktop         # Desktop application entry
│
├── Hotkey Daemon
│   ├── whisper_hotkey_daemon.py    # Background hotkey listener
│   ├── whisper_hotkey_recorder.py  # Recording helper
│   ├── whisper_hotkey_wayland.py   # Wayland-specific implementation
│   └── run_daemon.sh               # Daemon launcher
│
├── Integration Modules
│   ├── claude_integration.py       # Claude CLI proxy/integration
│   └── integration_example.py      # Generic REPL integration example
│
├── Configuration
│   ├── requirements.txt            # Python dependencies
│   ├── .claude/settings.local.json # Claude Code permissions
│   └── .gitignore                  # Git ignore rules
│
├── Documentation
│   ├── README.md                   # Main documentation
│   ├── FINAL_INSTRUCTIONS.md       # Daemon setup guide
│   ├── DEBUGGING_GUIDE.md          # Troubleshooting
│   ├── WHISPER_GUI_README.md       # GUI documentation
│   └── [Various other guides]
│
└── Testing & Debugging
    ├── check_real_session.py       # Session validation
    ├── comprehensive_debug.py      # Full diagnostics
    ├── simple_hotkey_test.py       # Hotkey testing
    └── [Various test scripts]
```

---

## Dependencies & Requirements

```
openai-whisper      # Speech-to-text model
pyaudio             # Microphone access
numpy               # Numerical computing
PyQt6               # GUI framework
psutil              # Process scanning
```

---

## Key Insights

1. **Multi-Instance Awareness:** The system is designed to discover and target specific CLI processes by scanning command-line strings for keywords ('claude', 'codex')

2. **Flexible Communication:** Three communication channels allow integration regardless of how the target CLI is structured:
   - Direct stdin injection (most direct)
   - Clipboard (fallback, compatible with any CLI)
   - Named pipes (for specialized workflows)

3. **Session Awareness:** Environment variables (`DISPLAY`, `WAYLAND_DISPLAY`) indicate session type and capabilities

4. **Modular Design:** Each component can be used independently or together:
   - Headless for scripting/automation
   - Interactive for manual use
   - GUI for advanced features
   - Daemon for system-wide hotkey support

5. **Process Isolation:** Uses `/proc/[pid]/fd/0` for isolated stdin communication, allowing the same Whisper instance to serve multiple different CLI processes simultaneously

---

## Technical Highlights

**Process Discovery Mechanism:**
- Uses `psutil.process_iter()` - efficient process scanning
- Looks for 'claude' or 'codex' in entire command line (case-insensitive)
- Stores both PID and process object reference for state management

**Headless Recognition Markers:**
- `--headless` flag in whisper_cli.py
- Suppresses interactive prompts
- Outputs only to stdout/FIFO/process stdin
- Single record-transcribe-output cycle

**Configuration Persistence:**
- Microphone selection: `~/.whisper/config` (JSON)
- GUI history: `~/.whisper/gui_history.json`
- Automatic location creation: `os.makedirs(..., exist_ok=True)`

