# Process Communication & Architecture Flows

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Whisper Multi-Layer System                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: Global Hotkey Integration (System-wide)              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  whisper_hotkey_daemon.py  (runs as sudo service)      │   │
│  │  - Monitors /dev/input/event* for CTRL+ALT+R          │   │
│  │  - Launches recording on hotkey trigger                │   │
│  │  - Copies transcription to clipboard                   │   │
│  │  - Works across ALL applications                       │   │
│  └──────────────┬──────────────────────────────────────────┘   │
│                 │                                                │
│  Layer 2: GUI Application (User-facing)                        │
│  ┌──────────────▼──────────────────────────────────────────┐   │
│  │  whisper_gui.py (PyQt6 Application)                    │   │
│  │  ┌────────────────────────────────────────────────────┐│   │
│  │  │ Process Discovery & Selection Module               ││   │
│  │  │ - Scans running processes with psutil             ││   │
│  │  │ - Finds 'claude' or 'codex' processes            ││   │
│  │  │ - Displays in dropdown: "claude (PID: 1234)"      ││   │
│  │  └────────────────────────────────────────────────────┘│   │
│  │  ┌────────────────────────────────────────────────────┐│   │
│  │  │ Recording & Transcription Thread                   ││   │
│  │  │ - Non-blocking QThread workers                     ││   │
│  │  │ - Uses WhisperCLI engine internally               ││   │
│  │  └────────────────────────────────────────────────────┘│   │
│  │  ┌────────────────────────────────────────────────────┐│   │
│  │  │ Multi-Channel Output                               ││   │
│  │  │ - stdin injection (/proc/[pid]/fd/0)             ││   │
│  │  │ - Clipboard (wl-copy for Wayland)               ││   │
│  │  │ - History persistence (JSON)                     ││   │
│  │  └────────────────────────────────────────────────────┘│   │
│  └──────────────┬──────────────────────────────────────────┘   │
│                 │                                                │
│  Layer 3: Core Engine (Reusable Module)                         │
│  ┌──────────────▼──────────────────────────────────────────┐   │
│  │  whisper_cli.py (WhisperCLI Class)                     │   │
│  │  - Audio device initialization (PyAudio)              │   │
│  │  - Recording with threading                           │   │
│  │  - Whisper model inference                            │   │
│  │  - Configuration management (~/.whisper/config)      │   │
│  │  - Multiple execution modes:                          │   │
│  │    * Headless (--headless): stdout output            │   │
│  │    * Interactive: REPL loop                           │   │
│  │    * FIFO: env WHISPER_TRANSCRIPT_FIFO output        │   │
│  └──────────────┬──────────────────────────────────────────┘   │
│                 │                                                │
│  Layer 4: Integration Modules                                   │
│  ┌──────────────▴──────────────────────────────────────────┐   │
│  │  ┌─────────────────────┐  ┌──────────────────────────┐ │   │
│  │  │ claude_integration  │  │ integration_example.py   │ │   │
│  │  │ (Claude proxy)      │  │ (Generic REPL pattern)   │ │   │
│  │  └─────────────────────┘  └──────────────────────────┘ │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Process Discovery & Communication Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                 GUI Startup & Process Discovery                │
└─────────────────────────────────────────────────────────────────┘

WhisperGUI.__init__()
    │
    ├─→ Load history from ~/.whisper/gui_history.json
    │
    ├─→ Create UI elements
    │   ├─ Start/Stop buttons
    │   ├─ Process dropdown (QComboBox)
    │   └─ History table
    │
    ├─→ refresh_cli_processes() [INITIAL SCAN]
    │   │
    │   ├─→ psutil.process_iter(['pid', 'name', 'cmdline'])
    │   │   │
    │   │   ├─→ Scan all processes
    │   │   │
    │   │   └─→ For each process:
    │   │       │
    │   │       ├─ Extract cmdline: ' '.join(proc.info['cmdline'])
    │   │       │
    │   │       ├─ Check: 'claude' in cmdline.lower() OR 
    │   │       │          'codex' in cmdline.lower()
    │   │       │
    │   │       └─ If Match:
    │   │           ├─ Extract cmd_name from path
    │   │           ├─ Format: f"{cmd_name} (PID: {pid})"
    │   │           └─ Store in: available_processes[display_name] = (pid, proc)
    │   │
    │   └─→ Populate dropdown with discovered processes
    │
    └─→ Connect signals
        ├─ process_combo.currentIndexChanged → on_process_selected()
        ├─ start_button.clicked → start_recording()
        └─ refresh_button.clicked → refresh_cli_processes()


┌─────────────────────────────────────────────────────────────────┐
│                  Recording & Output Flow                        │
└─────────────────────────────────────────────────────────────────┘

User clicks "Start Recording"
    │
    ├─→ start_recording()
    │   │
    │   ├─→ Create RecordingWorker(QObject)
    │   ├─→ Create QThread
    │   ├─→ moveToThread(worker)
    │   └─→ Connect signals & start thread
    │
    └─→ RecordingWorker.run() [in separate QThread]
        │
        ├─→ whisper.start_recording()
        │   ├─ Initialize PyAudio stream
        │   ├─ Start _record_audio() thread
        │   └─ Collect audio frames in self.audio_data
        │
        └─→ [User clicks Stop]
            │
            ├─→ RecordingWorker.stop() [signal]
            │
            └─→ whisper.stop_recording()
                │
                ├─→ Write audio to temp WAV file
                │
                ├─→ whisper.model.transcribe(audio_file)
                │   │
                │   └─→ [Whisper AI processes audio]
                │       │
                │       └─→ Returns: {"text": "transcribed text"}
                │
                ├─→ Get text from response
                │
                ├─→ Emit signal: result.emit(transcription_text)
                │
                └─→ [Back in main GUI thread]
                    │
                    ├─→ on_recording_result(transcription: str)
                    │
                    ├─→ Write to process stdin [IF selected]:
                    │   │
                    │   └─→ write_to_process_stdin(text)
                    │       │
                    │       ├─→ Get selected_process_pid from dropdown
                    │       │
                    │       ├─→ stdin_path = f"/proc/{pid}/fd/0"
                    │       │
                    │       ├─→ open(stdin_path, 'w')
                    │       │
                    │       ├─→ Write: text + '\n'
                    │       │
                    │       └─→ flush()
                    │           │
                    │           └─→ Text appears in target process stdin
                    │               (as if user typed it)
                    │
                    ├─→ Copy to clipboard [ALWAYS]:
                    │   │
                    │   └─→ subprocess.run(['wl-copy'], input=text)
                    │       (Wayland) or ['xclip', '-selection', 'clipboard']
                    │       (X11)
                    │
                    └─→ Add to history & refresh UI
```

---

## Headless Mode Execution Flow (For CLI Integration)

```
┌─────────────────────────────────────────────────────────────────┐
│  Usage: python whisper_cli.py --headless [--debug]             │
└─────────────────────────────────────────────────────────────────┘

main()
    │
    ├─→ argparse parses: --headless, --debug
    │
    ├─→ WhisperCLI(headless=True, debug=args.debug)
    │   │
    │   ├─→ self.headless = True
    │   │   └─→ Suppresses all interactive prompts
    │   │   └─→ Suppresses user-facing output (emojis, menus, etc.)
    │   │
    │   ├─→ Load Whisper model (once at startup)
    │   │
    │   ├─→ _select_microphone() 
    │   │   │
    │   │   ├─→ if headless:
    │   │   │   └─→ Use default input device (no prompting)
    │   │   │
    │   │   └─→ Load/save config to ~/.whisper/config
    │   │
    │   └─→ Set up signal handlers (SIGINT, SIGTERM)
    │
    ├─→ cli.run()
    │   │
    │   ├─→ if self.headless:
    │   │   └─→ run_headless()
    │   │       │
    │   │       ├─→ start_recording()
    │   │       │   ├─ Open PyAudio stream
    │   │       │   └─ Start recording thread
    │   │       │
    │   │       ├─→ input()  [Waits for ENTER on stdin]
    │   │       │
    │   │       ├─→ stop_recording()
    │   │       │   ├─ Stop stream & thread
    │   │       │   ├─ Save to temp WAV
    │   │       │   ├─ Run Whisper inference
    │   │       │   └─ Return transcription string
    │   │       │
    │   │       └─→ _write_to_fifo(transcript)
    │   │           │
    │   │           ├─→ Check: WHISPER_TRANSCRIPT_FIFO env var
    │   │           │
    │   │           ├─→ if set:
    │   │           │   └─→ Write transcript to FIFO
    │   │           │
    │   │           └─→ else:
    │   │               └─→ Print to stdout
    │   │
    │   └─→ cleanup()
    │       └─→ Close audio resources
    │
    └─→ exit(0)


Output Destinations (Priority):
    1. WHISPER_TRANSCRIPT_FIFO (if env var set) → Named pipe
    2. stdout (default) → Terminal or piped process
```

---

## Inter-Process Communication Mechanisms

```
┌──────────────────────────────────────────────────────────────┐
│  Method 1: Direct stdin Injection (/proc/[pid]/fd/0)        │
└──────────────────────────────────────────────────────────────┘

GUI Process (Whisper)         Target Process (Claude/Codex)
    │                                  │
    ├─→ Transcription complete         │
    │                                  │
    ├─→ selected_process_pid = 12345   │
    │   (from dropdown selection)       │
    │                                  │
    ├─→ open("/proc/12345/fd/0", 'w')  ──→ Targets process 12345's stdin
    │                                      (file descriptor 0)
    │
    ├─→ write("transcribed text\n")    ──→ Text written to process's input
    │                                      stream
    │
    └─→ flush()                        ──→ Process receives as if user typed
                                          then pressed ENTER


┌──────────────────────────────────────────────────────────────┐
│  Method 2: Clipboard Relay (Wayland)                        │
└──────────────────────────────────────────────────────────────┘

GUI Process (Whisper)              Wayland Clipboard
    │                                    │
    ├─→ Transcription complete           │
    │                                    │
    ├─→ subprocess.run(                  │
    │       ['wl-copy'],                 │
    │       input=text.encode()          │
    │   )                         ───→ Text written to clipboard
    │
    └─→ User can CTRL+V anywhere
        to paste transcription
        into target application


┌──────────────────────────────────────────────────────────────┐
│  Method 3: Named Pipe (FIFO)                                 │
└──────────────────────────────────────────────────────────────┘

Headless whisper_cli.py          External Process/Script
    │                                    │
    ├─→ export WHISPER_TRANSCRIPT_FIFO=/tmp/whisper.fifo
    │                              (env var set by caller)
    │
    ├─→ python whisper_cli.py --headless
    │
    ├─→ Transcription complete
    │
    ├─→ _write_to_fifo(transcript)
    │   │
    │   └─→ open(os.environ.get('WHISPER_TRANSCRIPT_FIFO'))
    │                                ───→ Write to named pipe
    │       │
    │       └─→ External process reads from FIFO
    │           and processes text


┌──────────────────────────────────────────────────────────────┐
│  Method 4: Hotkey Daemon → Clipboard                         │
└──────────────────────────────────────────────────────────────┘

[Any Application]
    │
    User presses CTRL+ALT+R
    │
    ├─→ hotkey_daemon.py detects via /dev/input/event*
    │
    ├─→ start_recording()
    │
    ├─→ User speaks into microphone
    │
    ├─→ User presses ENTER
    │
    ├─→ stop_recording() + transcribe()
    │
    ├─→ subprocess.run(['wl-copy'], input=text)
    │   │
    │   └─→ Text written to clipboard
    │
    └─→ User CTRL+V in any application
        └─→ Transcription appears!
```

---

## Process Identification Markers

```
┌─────────────────────────────────────────────────────────────┐
│     How Whisper Identifies Different CLI Instances          │
└─────────────────────────────────────────────────────────────┘

All Running Processes:
│
├─ bash          (PID: 1234) - Shell
├─ firefox       (PID: 5678) - Browser
├─ claude        (PID: 9012) ← MATCHES 'claude' keyword
├─ codex         (PID: 3456) ← MATCHES 'codex' keyword
├─ vim           (PID: 7890) - Text editor
├─ python3       (PID: 2468) - Could contain claude/codex in args
│  └─ cmdline: "python3 -m claude"  ← MATCHES 'claude'
└─ python3       (PID: 1357) - Generic Python
   └─ cmdline: "python3 my_script.py" - No match


Process Identification Algorithm:
═════════════════════════════════════════════════════════════

for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    │
    ├─→ Extract full command line:
    │   cmdline_str = ' '.join(proc.info['cmdline'])
    │   Example: "python3 -m claude --model gpt4"
    │
    ├─→ Check for match (case-insensitive):
    │   if 'claude' in cmdline_str.lower() OR
    │      'codex' in cmdline_str.lower():
    │
    ├─→ Extract process name:
    │   cmd_name = proc.info['cmdline'][0].split('/')[-1]
    │   Example: "claude" or "python3"
    │
    ├─→ Create display string:
    │   display_name = f"{cmd_name} (PID: {proc.pid})"
    │   Example: "claude (PID: 9012)"
    │
    └─→ Store for GUI dropdown:
        available_processes[display_name] = (proc.pid, proc)


Storage Structure in GUI:
═════════════════════════════════════════════════════════════

self.available_processes = {
    "claude (PID: 9012)": (9012, <Process obj>),
    "codex (PID: 3456)": (3456, <Process obj>),
    "python3 (PID: 2468)": (2468, <Process obj>),
}

self.process_combo (QComboBox) displays:
    ┌─────────────────────────────┐
    │ None                        │
    │ claude (PID: 9012)    ◄─ Selected
    │ codex (PID: 3456)           │
    │ python3 (PID: 2468)         │
    └─────────────────────────────┘

self.selected_process_pid = 9012
```

---

## State & Lifecycle Diagram

```
┌──────────────────────────────────────────────────────────────┐
│             WhisperCLI Lifecycle & State                     │
└──────────────────────────────────────────────────────────────┘

INITIALIZATION:
    │
    ├─→ __init__(headless, debug)
    │   ├─ Set flags
    │   ├─ Load Whisper model (one-time, GPU intensive)
    │   ├─ Initialize PyAudio
    │   ├─ Load microphone config or prompt for selection
    │   └─ Register signal handlers
    │
    ├─→ State after init:
    │   │
    │   ├─ self.headless = bool
    │   ├─ self.debug = bool
    │   ├─ self.model = whisper.load_model("medium")
    │   ├─ self.audio = pyaudio.PyAudio()
    │   ├─ self.input_device_index = int (or None)
    │   ├─ self.recording = False
    │   ├─ self.audio_data = []
    │   └─ self.stream = None
    │


RECORDING CYCLE:
    │
    ├─→ start_recording()
    │   │
    │   ├─ self.recording = True
    │   ├─ self.audio_data = []
    │   ├─ Open PyAudio stream (format=paInt16, channels=1, rate=16000)
    │   └─ Start _record_audio() thread
    │
    ├─→ _record_audio() [threaded]:
    │   │
    │   while self.recording and self.stream:
    │       ├─ Read frames from stream
    │       └─ Append to self.audio_data
    │
    ├─→ stop_recording()
    │   │
    │   ├─ self.recording = False
    │   ├─ Stop stream & thread
    │   ├─ Close stream
    │   ├─ Concatenate audio_data
    │   ├─ Write to temp WAV file
    │   ├─ Run whisper.model.transcribe(audio_file)
    │   ├─ Parse JSON response
    │   └─ Return transcription text
    │
    └─→ Back to ready state for next cycle


MULTIPLE EXECUTION PATHS:
    │
    ├─→ Interactive Mode (default):
    │   │
    │   run():
    │       while True:
    │           ├─ Prompt user
    │           ├─ User presses ENTER
    │           ├─ start_recording()
    │           ├─ User presses ENTER again
    │           ├─ transcript = stop_recording()
    │           ├─ Display transcript
    │           └─ [Loop continues]
    │
    ├─→ Headless Mode (--headless):
    │   │
    │   run_headless():
    │       ├─ start_recording()
    │       ├─ input()  [Waits for ENTER]
    │       ├─ transcript = stop_recording()
    │       ├─ Output to stdout/FIFO
    │       └─ cleanup() → exit
    │
    └─→ Configuration Mode (--configure):
        │
        _select_microphone() [interactive]:
            ├─ Show available devices
            ├─ Prompt for selection
            ├─ Save to ~/.whisper/config
            └─ exit


CLEANUP:
    │
    ├─→ cleanup()
    │   ├─ Stop spinner thread
    │   ├─ Close audio stream if open
    │   ├─ Terminate PyAudio
    │   └─ Exit
    │
    └─→ Signal Handlers (SIGINT, SIGTERM):
        ├─ Called on Ctrl+C or kill signal
        ├─ If recording, stop & get transcript
        ├─ cleanup()
        └─ exit
```

---

## Configuration & Environment Variables

```
┌──────────────────────────────────────────────────────────────┐
│         Configuration Loading & Persistence                  │
└──────────────────────────────────────────────────────────────┘

STARTUP:
    │
    ├─→ _load_config()
    │   │
    │   └─→ Try to read ~/.whisper/config
    │       │
    │       ├─→ File exists → Parse JSON
    │       │   └─→ Extract: input_device_index
    │       │   └─→ Return: True (config loaded)
    │       │
    │       └─→ File missing → Return: False
    │
    └─→ if not config:
        └─→ _select_microphone()
            ├─ List available devices
            ├─ Prompt user
            ├─ Get selection
            └─→ _save_config()
                └─→ Write to ~/.whisper/config
                    ```json
                    {
                      "input_device_index": 0
                    }
                    ```


ENVIRONMENT VARIABLES SCANNED/SET:
═════════════════════════════════════════════════════════════

Read at startup (_suppress_audio_warnings):
    ├─→ Set: ALSA_PCM_CARD = 'default'
    ├─→ Set: ALSA_PCM_DEVICE = '0'
    ├─→ if headless:
    │   ├─→ Set: JACK_NO_AUDIO_RESERVATION = '1'
    │   └─→ Set: PULSE_LATENCY_MSEC = '30'

Optional (for FIFO mode):
    ├─→ Check: WHISPER_TRANSCRIPT_FIFO
    │   └─→ if set: write transcript to this named pipe

GUI checks:
    ├─→ Check: WAYLAND_DISPLAY
    │   └─→ if set: use Wayland clipboard (wl-copy)
    │   └─→ else: use X11 clipboard (xclip)

Session detection (check_real_session.py):
    ├─→ Check: DISPLAY (X11 server)
    ├─→ Check: WAYLAND_DISPLAY (Wayland server)
    └─→ Check: XDG_VTNR (Virtual terminal number)
```

