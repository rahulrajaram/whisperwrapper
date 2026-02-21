# Whisper CLI Architecture Documentation Index

This directory now includes comprehensive documentation of the Whisper CLI system architecture, process identification mechanisms, and communication patterns.

## Documents Created

### 1. QUICK_REFERENCE.txt (12 KB)
**Best for:** Quick lookup, 5-minute overview, command cheat sheet

**Contains:**
- Core concept overview
- Process identification mechanism explained
- Three communication channels summary
- Execution modes & recognition markers
- Key files and locations
- Environment variables reference
- Code snippet examples
- Typical workflow walkthrough
- Debug commands
- Common issues & solutions
- Architecture layers diagram
- Process state machine

**Start here if you:** Need a quick answer, want to understand the system in 10 minutes

---

### 2. ARCHITECTURE_SUMMARY.md (11 KB)
**Best for:** High-level overview, understanding the big picture

**Contains:**
- How it identifies different CLIs
- Three communication channels (detailed)
- Four key entry points (headless, interactive, GUI, daemon)
- Configuration & environment variables
- Process state tracking
- Distinguishing multiple CLI instances
- Code organization
- Dependencies
- Key technical details
- Integration patterns
- Real-world usage examples
- Debugging & testing commands
- Summary of design principles

**Start here if you:** Want a clear understanding of the overall architecture in 15-20 minutes

---

### 3. CLI_Architecture_Analysis.md (15 KB)
**Best for:** Detailed technical understanding, code analysis

**Contains:**
- Project overview
- Detailed component breakdown:
  - whisper_cli.py (Core engine)
  - whisper (Shell wrapper)
  - whisper_gui.py (GUI)
  - whisper_hotkey_daemon.py (Hotkey daemon)
- Process identification & discovery mechanisms
- Communication channels (with code examples)
- Environment variables (comprehensive list)
- Configuration files & persistence
- Launch methods & execution modes
- Code entry points for each module
- Process state & control flow
- Integration patterns (3 types)
- Process distinction mechanisms
- File structure summary
- Dependencies & requirements
- Key insights & technical highlights

**Start here if you:** Want to understand every component, understand code behavior, need technical depth

---

### 4. Process_Communication_Flows.md (27 KB)
**Best for:** Visual learners, understanding flows, state machines, algorithms

**Contains:**
- System architecture diagram (ASCII art)
- Process discovery & communication flow
- Headless mode execution flow
- Inter-process communication mechanisms (4 types):
  - Direct stdin injection
  - Clipboard relay
  - Named pipe (FIFO)
  - Hotkey daemon → clipboard
- Process identification markers & algorithm
- State & lifecycle diagram
- Configuration & environment variable flows
- Storage structure examples

**Start here if you:** Want to see flow diagrams, understand state machines, learn algorithms

---

### 5. Existing Documentation (For Reference)
- **README.md** - User-facing documentation, quick start guide
- **FINAL_INSTRUCTIONS.md** - Hotkey daemon setup and usage
- **DEBUGGING_GUIDE.md** - Troubleshooting guide
- **WHISPER_GUI_README.md** - GUI-specific documentation
- **GETTING_STARTED_GUI.md** - GUI quick start

---

## How to Navigate

### If you have 5 minutes:
1. Read: QUICK_REFERENCE.txt
2. Skim: "Core Concept" and "Key Identification Mechanism" sections

### If you have 15 minutes:
1. Read: ARCHITECTURE_SUMMARY.md
2. Focus on: "How It Identifies Different CLIs" section
3. Skim: "Three Communication Channels"

### If you have 30 minutes:
1. Read: ARCHITECTURE_SUMMARY.md (full)
2. Skim: CLI_Architecture_Analysis.md sections on components you care about

### If you want complete understanding:
1. Read: ARCHITECTURE_SUMMARY.md (overview)
2. Read: CLI_Architecture_Analysis.md (details)
3. Reference: Process_Communication_Flows.md (diagrams & flows)
4. Consult: QUICK_REFERENCE.txt (for specific lookups)

### If you want to understand the code:
1. Read: ARCHITECTURE_SUMMARY.md "Key Technical Details" section
2. Read: CLI_Architecture_Analysis.md "Code Entry Points" section
3. Reference: Process_Communication_Flows.md "Process Identification Markers" algorithm
4. Look at: Source code with these sections as guide:
   - whisper_cli.py line 472+ (main entry point)
   - whisper_gui.py line 467-510 (process discovery)
   - whisper_gui.py line 515-536 (stdin communication)

---

## Key Concepts at a Glance

### Process Identification
```python
# Whisper finds CLI processes by scanning
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    if 'claude' in ' '.join(proc.info['cmdline']).lower():
        # Found a Claude process!
        print(f"{proc.info['name']} (PID: {proc.pid})")
```

### Communication Method 1: stdin Injection
```python
# Write directly to process's input stream
stdin_path = f"/proc/{pid}/fd/0"
with open(stdin_path, 'w') as f:
    f.write(transcribed_text + '\n')
```

### Communication Method 2: Clipboard
```python
# Write to clipboard (Wayland)
subprocess.run(['wl-copy'], input=transcribed_text.encode())
```

### Communication Method 3: FIFO
```bash
# Via environment variable
export WHISPER_TRANSCRIPT_FIFO=/tmp/whisper.fifo
python whisper_cli.py --headless
```

### Headless Mode Recognition
- **Invocation:** `python whisper_cli.py --headless`
- **Code:** `self.headless = True` suppresses prompts
- **Behavior:** Single cycle, no emoji output, outputs only text

---

## File Descriptions

| Document | Size | Lines | Purpose | Best For |
|----------|------|-------|---------|----------|
| QUICK_REFERENCE.txt | 12 KB | 500+ | Cheat sheet, quick lookup | Quick answers |
| ARCHITECTURE_SUMMARY.md | 11 KB | 400+ | High-level overview | Big picture |
| CLI_Architecture_Analysis.md | 15 KB | 500+ | Component breakdown | Technical depth |
| Process_Communication_Flows.md | 27 KB | 800+ | Flows, diagrams, algorithms | Visual learning |

**Total:** 65+ KB of documentation, 2000+ lines of technical content

---

## Cross-References

### How Process Identification Works
- QUICK_REFERENCE.txt: "Key Identification Mechanism"
- ARCHITECTURE_SUMMARY.md: "How It Identifies Different CLIs"
- CLI_Architecture_Analysis.md: "Process Identification & Discovery"
- Process_Communication_Flows.md: "Process Identification Markers"

### Communication Channels
- QUICK_REFERENCE.txt: "Three Communication Channels"
- ARCHITECTURE_SUMMARY.md: "Three Communication Channels"
- CLI_Architecture_Analysis.md: "Communication Channels"
- Process_Communication_Flows.md: "Inter-Process Communication Mechanisms"

### Execution Modes
- QUICK_REFERENCE.txt: "Execution Modes & Recognition"
- ARCHITECTURE_SUMMARY.md: "Key Entry Points"
- CLI_Architecture_Analysis.md: "Launch Methods & Execution Modes"
- Process_Communication_Flows.md: "Headless Mode Execution Flow"

### Code Entry Points
- CLI_Architecture_Analysis.md: "Code Entry Points"
- QUICK_REFERENCE.txt: "Code Snippets - Key Patterns"
- Source files:
  - whisper_cli.py line 472-509 (main)
  - whisper_gui.py line 74-120 (__init__)
  - whisper_hotkey_daemon.py line 200+ (main)

---

## Quick Troubleshooting Reference

**Whisper doesn't detect my Claude/Codex process:**
- See: QUICK_REFERENCE.txt "Common Issues & Solutions"
- See: ARCHITECTURE_SUMMARY.md "Distinguishing Multiple CLI Instances"
- Check: Process has 'claude' or 'codex' in command line

**stdin injection doesn't work:**
- See: QUICK_REFERENCE.txt "Common Issues & Solutions"
- Fallback: Clipboard method (always works)
- Check: `/proc/[pid]/fd/0` is accessible

**Hotkey daemon won't listen to my keystrokes:**
- See: FINAL_INSTRUCTIONS.md "Troubleshooting"
- Issue: Running from SSH or IDE terminal (not desktop terminal)
- Check: DISPLAY or WAYLAND_DISPLAY environment variables

**I need to understand the state machine:**
- See: Process_Communication_Flows.md "State & Lifecycle Diagram"
- See: QUICK_REFERENCE.txt "Process State Machine"

---

## Source Code Files Referenced

- **whisper_cli.py** - Core WhisperCLI class
  - Lines 19-50: `__init__()` 
  - Lines 424-443: Execution modes
  - Lines 472-509: `main()` entry point
  
- **whisper_gui.py** - GUI with process integration
  - Lines 74-120: `__init__()` and UI setup
  - Lines 467-510: `refresh_cli_processes()` - process discovery
  - Lines 515-536: `write_to_process_stdin()` - stdin communication
  
- **whisper_hotkey_daemon.py** - Hotkey listener
  - Lines 39-200+: Device finding and initialization

---

## How This Documentation Was Created

This documentation was created through:
1. **Project exploration** - Examined all source files and scripts
2. **Code analysis** - Analyzed key functions and class structures
3. **Architecture mapping** - Documented relationships and flows
4. **Documentation generation** - Created documents at different detail levels

All documents are:
- Self-contained (can be read independently)
- Cross-referenced (linked between documents)
- Based on actual code (not speculation)
- Organized by detail level (quick → detailed)

---

## Summary

The Whisper CLI system is a multi-layer, process-aware voice-to-text engine that:

1. **Identifies** CLI processes by scanning system processes for 'claude' or 'codex' keywords
2. **Communicates** via three channels: stdin injection, clipboard, or named pipes
3. **Integrates** in multiple ways: function import, proxy, GUI selection, system hotkey
4. **Operates** in multiple modes: interactive, headless, GUI, daemon
5. **Tracks** state through a clean lifecycle: init → config → ready → recording → transcribing → output → cleanup

All of this is documented comprehensively in these four documents, with different levels of detail to suit different needs.

---

**Last Updated:** November 2, 2025  
**Documentation Created:** November 2, 2025  
**Location:** `/home/rahul/Documents/whisper/`

