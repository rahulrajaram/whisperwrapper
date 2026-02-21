# Test Fixture Guide

This repository now ships with a collection of lightweight test doubles so we can
exercise GUI/CLI/daemon code without needing PyQt, Whisper, DBus, or actual audio
devices at runtime. When extending the suite, prefer these helpers over ad-hoc
stubs so coverage stays high and the intent remains clear.

## Qt / GUI Helpers

- `tests/conftest.py` exports a session-scoped `qt_app` fixture that spins up a
  headless `QApplication`. Use it in any test that instantiates Qt widgets.
- `tests/test_gui_helpers.py` defines reusable dummy widgets (buttons, combo boxes,
  layouts) plus the `FakeGUIForActions` container. Import those classes when you
  need to simulate GUI interactions without a real window manager.
- `tests/test_main_window.py` shows how to patch `WhisperPresenter`, `HotkeyBackend`,
  `GUIStorageManager`, and `CommandBus` with in-memory variants so you can drive
  the entire `WhisperGUI` lifecycle without touching audio hardware.

## CLI / Service Doubles

- `tests/test_cli_runner.py` mocks `WhisperRecordingController` and the spinner
  thread to verify CLI behavior (microphone selection, headless runs, main entry
  point) deterministically.
- `tests/test_services.py` provides stub implementations for PyAudio, Whisper
  models, and Wave writes. These keep audio/transcription tests fast while still
  covering serialization and error paths.

## IPC / Daemon Stubs

- `tests/test_command_bus_and_fifo.py` exercises FIFO creation and dispatch using
  fake threads and file handles—use it as a blueprint for additional FIFO logic.
- `tests/test_dbus_controller.py` bundles mock SessionBus/DBus classes so you can
  hit fallback and stop logic without a real DBus daemon.
- `tests/test_hotkey_backend.py` stubs out `pynput` and the listener thread so
  we can exercise the shared `HotkeyBackend` without needing system-level
  hooks.
- `tests/helpers.py` ships `ensure_whisper_module()` which loads the real
  Whisper package when `WHISPER_TESTS_FORCE_REAL=1` or installs a deterministic
  stub otherwise. Integration tests always exercise the transcription path,
  even on machines without the upstream dependency.

When adding new tests:

1. Reuse or extend the existing stub classes instead of inventing new ones.
2. Keep fixtures near the tests that use them; if you expect multiple modules to
   share a stub, document it here and move it into a dedicated helper module.
3. Run `PYTHONPATH=src QT_QPA_PLATFORM=offscreen venv/bin/python -m pytest --cov`
   to ensure new coverage is counted.
