"""Lightweight GUI integration smoke test."""

from __future__ import annotations

import pytest

from whisper_app.gui import main_window as gui_module


def test_whisper_gui_smoke(monkeypatch, tmp_path, qt_app):
    """Use the real presenter stack but stub out side-effecting services."""

    class StubRecordingController:
        def __init__(self, *_, **__):
            self.recording = False

        def cleanup(self):
            self.cleaned = True

    class StubHotkeyBackend:
        def __init__(self, *_, **__):
            self.stopped = False

        def start(self):
            pass

        def stop(self):
            self.stopped = True

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(gui_module, "WhisperRecordingController", lambda *a, **k: StubRecordingController())
    monkeypatch.setattr(gui_module, "HotkeyBackend", StubHotkeyBackend)

    window = gui_module.WhisperGUI()
    window.exit_app()
