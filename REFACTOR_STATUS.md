# Refactor Plan

- [ ] Surface The Baseline
  - [ ] Generate a module + dependency map (e.g., via `pydeps`) and capture the hotkey event chain (HotkeyBackend → FIFO → `CommandController` → GUI) in docs so contributors have a single source of truth.
  - [ ] Add structured logging / tracing toggled by env vars in the GUI/HotkeyBackend stack to confirm where the Ctrl+Alt+Shift+R signal dies.
  - [ ] Provide an automated diagnostics script that checks FIFO existence, PID lock, and keystroke capture so regressions are reproducible before any refactor begins.

- [ ] Carve Out Core Services
  - [x] Split `WhisperCLI` in `src/whisper_app/cli.py:19` into `AudioInputService`, `RecordingSession`, and `TranscriptionService` to isolate responsibilities.
  - [x] Move shared configuration (paths, device ids, model options) into `whisper_app/config.py` so GUI, CLI, and daemons use the same schema.
  - [x] Introduce an event-oriented `RecordingController` interface that exposes start/stop/toggle hooks for GUI workers and daemons.

- [ ] Unify Hotkey + IPC Layers
- [x] Replace duplicated `pynput` listeners by consolidating on the shared `HotkeyBackend` inside the GUI (legacy daemon removed).
  - [x] Wrap FIFO/DBus specifics behind a `CommandBus` built on `CommandController` (`src/whisper_app/ipc_controller.py:33`) with a documented command contract.
  - [x] Make hotkey configuration (key chord, enable/disable daemon) part of the shared config and surface it in the GUI.

- [ ] Modularize The GUI
  - [x] Break `src/whisper_app/gui.py` into submodules (`gui/main_window.py`, `gui/ui.py`, `gui/workers/recording.py`, `gui/workers/codex.py`).
  - [x] Add a ViewModel/presenter layer that mediates between UI widgets and `RecordingController` to keep business logic out of PyQt components.
  - [x] Extract persistence tasks (history file, lock file) into a `StorageService` with clear error handling and test coverage.

- [ ] Strengthen Process Coordination
  - [ ] Introduce a `ProcessRegistry` that manages PID lock files, FIFO paths, and health endpoints instead of ad-hoc file writes (`src/whisper_app/gui.py:339`).
  - [ ] Ensure all long-lived threads (recording worker, hotkey listener, IPC reader) report status through a shared health interface.
  - [ ] Build a `whisperctl status|start|stop|diagnose` CLI that exercises IPC and hotkey flows end to end.

- [ ] Testing & Automation
  - [ ] Expand unit tests with PyAudio/Torch mocks for the new services plus hotkey-to-command integration tests using FIFO fixtures.
  - [ ] Add regression tests for hotkey handling and history persistence.
  - [ ] Wire diagnostics + new service tests into CI so hotkey/IPC regressions fail early.

- [ ] Documentation & Developer Tooling
  - [ ] Update `docs/MULTI_OS_ARCHITECTURE.md` with current service boundaries and sequence diagrams.
  - [ ] Extend contributing notes with instructions to run individual services (hotkey backend, GUI with stub recorder) for agentic tooling workflows.
