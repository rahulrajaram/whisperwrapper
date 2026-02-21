# Whisper CLI Architecture - Executive Summary

## Quick Reference

**Project:** Speech-to-text system with multi-layer CLI integration  
**Location:** `/home/rahul/Documents/whisper/`  
**Key Purpose:** Identify and communicate with different CLI processes (Claude, Codex, etc.) for voice input

---

## How It Identifies Different CLIs

The system uses **process scanning + keyword matching**:

```python
# Scan all running processes
for process in psutil.process_iter(['pid', 'name', 'cmdline']):
    full_command = ' '.join(process.info['cmdline'])
    
    # Match against known CLI names (case-insensitive)
    if 'claude' in full_command.lower() or 'codex' in full_command.lower():
        # Found a matching process!
        # Store with: (process_id, process_object)
```

**Identification Markers:**
- **Process ID (PID):** Unique system identifier
- **Command-line keyword:** 'claude' or 'codex' string in full command
- **File descriptor:** Each process has `/proc/[pid]/fd/0` for stdin
- **Display name:** Shows as "claude (PID: 1234)" in GUI dropdown

---

## Three Communication Channels

### 1. Direct stdin Injection (Most Direct)
```
GUI detects transcription
    ↓
Opens: /proc/[pid]/fd/0
    ↓
Writes: transcribed text + newline
    ↓
Process receives as if user typed it
```

**Mechanism:** `open(f"/proc/{process_id}/fd/0", 'w')` → write text

### 2. Clipboard (Fallback)
```
GUI detects transcription
    ↓
subprocess.run(['wl-copy'], input=text)  [Wayland]
    ↓
User CTRL+V in any application
```

### 3. Named Pipe/FIFO (Scripting)
```
export WHISPER_TRANSCRIPT_FIFO=/tmp/whisper.fifo
python whisper_cli.py --headless
    ↓
Transcription written to FIFO
    ↓
External script reads from FIFO
```

**Environment variable:** `WHISPER_TRANSCRIPT_FIFO`

---

## Key Entry Points

### 1. Headless Mode (for scripting/automation)
```bash
python whisper_cli.py --headless [--debug]
```
- Single record-transcribe cycle
- No interactive prompts
- Outputs only transcription to stdout or FIFO

**Recognition markers:**
- `--headless` flag
- `self.headless = True` in WhisperCLI class
- Suppresses all user-facing emoji/menu output

### 2. Interactive Mode (user-facing CLI)
```bash
./whisper
# or
python whisper_cli.py --debug
```
- REPL loop with prompts
- Press ENTER to record/stop
- Displays friendly output with emojis

### 3. GUI Application (advanced features)
```bash
python whisper_gui.py
# or via desktop menu
```
- Process discovery & selection dropdown
- Multi-threaded recording (non-blocking UI)
- History persistence & clipboard management
- Real-time process scanning

### 4. Hotkey Daemon (system-wide)
```bash
sudo ./run_daemon.sh --debug
# or systemd service
systemctl --user enable whisper-hotkey
```
- Monitors `/dev/input/event*` for CTRL+ALT+R
- Works in any application
- Copies result to clipboard

---

## Configuration & Environment

### Files
- **Microphone config:** `~/.whisper/config` (JSON, stores device index)
- **GUI history:** `~/.whisper/gui_history.json` (JSON, timestamps + text)
- **Project settings:** `.claude/settings.local.json` (permissions for Claude Code)

### Environment Variables Set by System
- `ALSA_PCM_CARD=default` - Audio configuration
- `ALSA_PCM_DEVICE=0` - Audio device
- `JACK_NO_AUDIO_RESERVATION=1` - Suppress JACK (headless mode)
- `PULSE_LATENCY_MSEC=30` - PulseAudio latency (headless mode)

### Environment Variables Checked
- `DISPLAY` - X11 session indicator
- `WAYLAND_DISPLAY` - Wayland session indicator
- `WHISPER_TRANSCRIPT_FIFO` - Optional FIFO path for output

---

## Process State Tracking

**Key instance variables in WhisperCLI:**

```python
self.headless          # bool - execution mode flag
self.debug             # bool - debug output flag
self.recording         # bool - current recording state
self.audio_data        # list - audio frames buffer
self.input_device_index # int - selected microphone
self.stream            # PyAudio stream object
self.config_file       # str - path to config
```

**Flow states:**
```
INIT → CONFIG (load/configure microphone) → READY → 
RECORDING → TRANSCRIBING → OUTPUT → READY [loop]
                                       ↓
                                    CLEANUP
```

---

## Distinguishing Multiple CLI Instances

The GUI can serve multiple different CLI processes simultaneously:

```
GUI.available_processes = {
    "claude (PID: 9012)": (9012, <Process obj>),
    "codex (PID: 3456)": (3456, <Process obj>),
    "python3 (PID: 2468)": (2468, <Process obj>),
}

User selects "claude (PID: 9012)" from dropdown
    ↓
On transcription, writes to: /proc/9012/fd/0
    ↓
Text goes ONLY to process 9012's stdin
(Other processes are unaffected)
```

**What makes each unique:**
1. **PID** - System-assigned process identifier
2. **cmdline** - Full command string in `/proc/[pid]/cmdline`
3. **stdin FD** - Each process has isolated `/proc/[pid]/fd/0`
4. **Environment** - Each process has own env vars (DISPLAY, etc.)

---

## Code Organization

```
/home/rahul/Documents/whisper/
│
├─ whisper_cli.py              # Core engine (WhisperCLI class)
├─ whisper                     # Shell wrapper (suppresses ALSA warnings)
├─ whisper_gui.py              # GUI with process detection
├─ whisper_hotkey_daemon.py    # System hotkey listener
│
├─ claude_integration.py       # Claude CLI proxy/integration
├─ integration_example.py      # Generic REPL integration template
│
├─ launch_gui.sh               # GUI launcher with dependency check
├─ run_daemon.sh               # Daemon launcher
│
├─ CLI_Architecture_Analysis.md        # Detailed architecture document
├─ Process_Communication_Flows.md      # Flow diagrams & state machines
└─ [Documentation files]
```

---

## Dependencies

```
openai-whisper      # Speech-to-text model
pyaudio             # Microphone access
numpy               # Numerical computing
PyQt6               # GUI framework
psutil              # Process scanning
evdev               # Keyboard event monitoring (daemon only)
```

---

## Key Technical Details

### Process Discovery Algorithm
1. Iterate over all processes: `psutil.process_iter(['pid', 'name', 'cmdline'])`
2. Extract full command: `' '.join(proc.info['cmdline'])`
3. Match pattern: `'claude' in cmd.lower() OR 'codex' in cmd.lower()`
4. Store with display format: `f"{cmd_name} (PID: {pid})"`

### stdin Communication Mechanism
1. GUI has: `self.selected_process_pid = 9012` (from dropdown)
2. On transcription: `stdin_path = f"/proc/9012/fd/0"`
3. Write operation: `open(stdin_path, 'w')` → `write(text + '\n')` → `flush()`
4. Result: Text delivered to process's stdin as if user typed it

### Headless Mode Recognition
- **CLI argument:** `--headless` flag
- **Class state:** `self.headless = True` in WhisperCLI
- **Behavior:** 
  - Suppresses all interactive prompts
  - Single record → transcribe → output → exit cycle
  - No emoji/menu output
  - Outputs only to stdout/FIFO

### Session Type Detection
- **Wayland:** `WAYLAND_DISPLAY` is set → use `wl-copy` for clipboard
- **X11:** `DISPLAY` is set → use `xclip` for clipboard
- **Headless/SSH:** Neither set → FIFO mode only

---

## Integration Patterns

### Pattern 1: In-Process Function Import
```python
from whisper_recorder import handle_voice_command
if user_input == '/voice':
    transcribed = handle_voice_command()
    process_input(transcribed)
```

### Pattern 2: Proxy Subprocess
```python
# claude_integration.py
subprocess.Popen(['claude'], stdin=subprocess.PIPE)
# Intercepts commands and manages I/O
```

### Pattern 3: GUI with Process Selection
```
User runs: python whisper_gui.py
GUI scans processes → finds "claude (PID: 9012)"
User selects it from dropdown
User clicks "Start Recording"
On completion, GUI writes to /proc/9012/fd/0
Text appears in Claude's input!
```

---

## Real-World Usage Examples

### Example 1: Integration in Existing Claude CLI
```python
# Inside Claude's REPL loop
if user_input == '/voice':
    from claude_integration import handle_voice_command
    voice_text = handle_voice_command()
    if voice_text:
        user_input = voice_text  # Process as normal input
```

### Example 2: Standalone Headless Integration
```bash
# In a script
export WHISPER_TRANSCRIPT_FIFO=/tmp/whisper.fifo
mkfifo /tmp/whisper.fifo
python whisper_cli.py --headless &
# Read transcription from FIFO
cat /tmp/whisper.fifo
```

### Example 3: GUI with Multiple CLIs Running
```bash
# Terminal 1: Claude
claude

# Terminal 2: Codex
codex

# Terminal 3: Whisper GUI
python whisper_gui.py
# GUI dropdown will show both processes
# User can select which one to send transcriptions to
```

---

## Debugging & Testing

**Check session type:**
```bash
python check_real_session.py
# Shows DISPLAY, WAYLAND_DISPLAY, keyboard access status
```

**Run with debug output:**
```bash
python whisper_cli.py --debug
# Prints DEBUG: messages to stderr
```

**Scan processes:**
```bash
python whisper_gui.py
# Prints "Found X CLI process(es)" in status bar
```

**Full diagnostics:**
```bash
python comprehensive_debug.py
# Complete system analysis
```

---

## Files for Further Reference

1. **CLI_Architecture_Analysis.md** - Detailed component breakdown, code analysis
2. **Process_Communication_Flows.md** - Flow diagrams, state machines, algorithm details
3. **README.md** - User-facing documentation
4. **FINAL_INSTRUCTIONS.md** - Hotkey daemon setup guide
5. **DEBUGGING_GUIDE.md** - Troubleshooting help

---

## Summary

The Whisper system is designed as a **multi-layer, process-aware voice input engine** that can:

1. **Identify** different CLI processes by scanning system processes for 'claude' or 'codex' keywords
2. **Target** specific processes using their Process ID and stdin file descriptor (`/proc/[pid]/fd/0`)
3. **Integrate** in multiple ways: in-process, proxy subprocess, GUI selection, system hotkey
4. **Operate** in multiple modes: interactive, headless (scripting), GUI (advanced), daemon (system-wide)
5. **Communicate** via three channels: direct stdin injection, clipboard, or named pipes (FIFO)

This architecture enables transparent voice input integration across different CLI applications while maintaining isolation between processes and flexible deployment options.

