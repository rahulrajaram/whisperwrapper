"""Tests for WhisperGUI main window wiring."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from PyQt6.QtCore import QObject, pyqtSignal

from whisper_app.gui import main_window as module


class StubRuntimeConfig:
    def __init__(self, *_, **__):
        self.paths = SimpleNamespace(history_file="history.json")
        self.hotkeys = SimpleNamespace(enabled=False, chord="ctrl+alt+r")


class StubStorage:
    def __init__(self, _paths):
        self.data = [{"timestamp": "t1", "text": "hello", "protected": False}]

    def load_history(self):
        return list(self.data)

    def save_history(self, history):
        self.data = list(history)


class StubPresenter(QObject):
    recording_started = pyqtSignal()
    recording_finished = pyqtSignal()
    recording_error = pyqtSignal(str)
    recording_status = pyqtSignal(str)
    transcription_ready = pyqtSignal(str)
    history_changed = pyqtSignal()
    status_message = pyqtSignal(str)
    codex_started = pyqtSignal()
    codex_finished = pyqtSignal()
    codex_error = pyqtSignal(str)

    def __init__(self, *_args, **_kwargs):
        super().__init__()
        self.is_recording = False
        self.history = [{"timestamp": "t1", "text": "alpha", "protected": False}]
        self.selected_row = None
        self.codex_calls = 0

    def start_recording(self):
        if self.is_recording:
            return False
        self.is_recording = True
        self.recording_started.emit()
        return True

    def stop_recording(self):
        self.is_recording = False
        self.recording_finished.emit()

    def process_with_codex(self):
        self.codex_calls += 1
        self.codex_started.emit()
        self.codex_finished.emit()

    def clear_history(self):
        self.history.clear()
        self.history_changed.emit()

    def toggle_row_selection(self, row: int):
        self.selected_row = None if self.selected_row == row else row
        return self.selected_row

    def shutdown(self):
        self.is_recording = False

    def wait_for_recording(self):
        self.is_recording = False


class StubCommandBus:
    def __init__(self, *_args, **_kwargs):
        self.handlers = {}

    def subscribe(self, name, handler):
        self.handlers[name] = handler

    def start(self):
        pass

    def stop(self):
        pass


class StubHotkeyBackend:
    def __init__(self, *_, **__):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class StubRecordingController:
    def cleanup(self):
        self.cleaned = True


class StubCallbacks:
    def __init__(self, **kwargs):
        self.on_error = kwargs.get("on_error")


@pytest.fixture
def patched_window(monkeypatch, qt_app):
    monkeypatch.setattr(module, "WhisperRuntimeConfig", StubRuntimeConfig)
    monkeypatch.setattr(module, "GUIStorageManager", StubStorage)
    monkeypatch.setattr(module, "WhisperPresenter", StubPresenter)
    monkeypatch.setattr(module, "CommandBus", StubCommandBus)
    monkeypatch.setattr(module, "HotkeyBackend", StubHotkeyBackend)
    monkeypatch.setattr(module, "WhisperRecordingController", lambda *_, **__: StubRecordingController())
    monkeypatch.setattr(module, "RecordingEventCallbacks", StubCallbacks)

    class DummyController:
        pass

    window = module.WhisperGUI(command_controller=DummyController())
    return window


def test_whisper_gui_recording_flow(patched_window):
    window = patched_window
    window._on_toggle_command()
    window._on_controller_error("boom")
    assert window.start_recording() is None
    window.stop_recording()
    window.presenter.recording_finished.emit()
    window._on_presenter_transcription_ready("text")
    window._on_presenter_status_message("status")
    window._on_codex_error("err")
    window.exit_app()


def test_whisper_gui_history_and_codex(patched_window):
    window = patched_window
    window.refresh_history_table()
    window.on_table_cell_clicked(0, 1)
    window.clear_history()
    window.on_codex_button_clicked()
    assert window.presenter.codex_calls == 1
    window.refresh_history_table()
