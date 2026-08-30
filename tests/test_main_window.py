"""Tests for WhisperGUI main window wiring."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QObject, pyqtSignal

from whisper_app.recipes import Recipe
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
    projects_changed = pyqtSignal()

    def __init__(self, *_args, **_kwargs):
        super().__init__()
        self.is_recording = False
        self.history = [{"timestamp": "t1", "text": "alpha", "protected": False}]
        self.selected_row = None
        self.selected_rows = set()  # For multi-select support
        self.last_selected_row = None
        self.codex_calls = 0
        self.copied_text: list[str] = []
        self.project_manager = MagicMock()

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

    def get_filtered_history(self, project_id=None):
        """Return history filtered by project (for testing, return all)."""
        return self.history

    def copy_text_to_clipboard(self, text: str):
        self.copied_text.append(text)
        return True

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


class StubSoundEffect:
    class Status:
        Ready = "ready"
        Error = "error"

    def __init__(self, *_args, **_kwargs):
        self.statusChanged = MagicMock()
        self.source = None
        self.play_calls = 0

    def setSource(self, source):
        self.source = source

    def status(self):
        return self.Status.Ready

    def play(self):
        self.play_calls += 1


@pytest.fixture
def patched_window(monkeypatch, qt_app):
    monkeypatch.setattr(module, "WhisperRuntimeConfig", StubRuntimeConfig)
    monkeypatch.setattr(module, "GUIStorageManager", StubStorage)
    monkeypatch.setattr(module, "WhisperPresenter", StubPresenter)
    monkeypatch.setattr(module, "CommandBus", StubCommandBus)
    monkeypatch.setattr(module, "HotkeyBackend", StubHotkeyBackend)
    monkeypatch.setattr(
        module, "WhisperRecordingController", lambda *_, **__: StubRecordingController()
    )
    monkeypatch.setattr(module, "RecordingEventCallbacks", StubCallbacks)
    monkeypatch.setattr(module, "ProjectManager", lambda *_, **__: MagicMock())
    monkeypatch.setattr(module, "QSoundEffect", StubSoundEffect)
    monkeypatch.setattr(module, "_completion_sound_path", lambda: Path(__file__))

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
    assert window.completion_sound is not None
    assert window.completion_sound.play_calls == 2
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


def test_whisper_gui_subscribes_to_history_picker_command(patched_window):
    assert "history" in patched_window.command_bus.handlers


def test_visible_transcript_picker_is_explicitly_activated(
    patched_window,
    monkeypatch,
):
    class StubPicker:
        def __init__(self):
            self.show_calls = 0
            self.raise_calls = 0
            self.activate_calls = 0

        def isVisible(self):
            return True

        def showNormal(self):
            self.show_calls += 1

        def raise_(self):
            self.raise_calls += 1

        def activateWindow(self):
            self.activate_calls += 1

        def winId(self):
            return 456

        def deleteLater(self):
            raise AssertionError("live picker must not be discarded")

    activated: list[str | None] = []
    picker = StubPicker()
    patched_window._transcript_picker = picker
    monkeypatch.setattr(
        module.QTimer,
        "singleShot",
        lambda _delay, callback: callback(),
    )
    monkeypatch.setattr(
        module,
        "activate_x11_window",
        lambda window_id: activated.append(window_id) or True,
    )
    monkeypatch.setattr(module, "x11_window_exists", lambda _window_id: True)

    patched_window.show_transcript_picker()

    assert picker.show_calls == 1
    assert picker.raise_calls == 2
    assert picker.activate_calls == 2
    assert activated == ["456"]


def test_destroyed_transcript_picker_is_discarded_and_recreated(
    patched_window,
    monkeypatch,
):
    class StalePicker:
        def __init__(self):
            self.deleted = False

        def isVisible(self):
            return True

        def winId(self):
            return 456

        def deleteLater(self):
            self.deleted = True

    stale = StalePicker()
    patched_window._transcript_picker = stale
    monkeypatch.setattr(module, "x11_window_exists", lambda _window_id: False)
    monkeypatch.setattr(module, "active_x11_window", lambda: "123")
    monkeypatch.setattr(patched_window, "_focus_transcript_picker", lambda: None)

    patched_window.show_transcript_picker()

    assert stale.deleted is True
    assert patched_window._transcript_picker is not stale
    assert patched_window._transcript_target_window == "123"


def test_selected_transcript_is_copied_restored_and_pasted(
    patched_window,
    monkeypatch,
):
    restored: list[str | None] = []
    pasted: list[bool] = []
    patched_window._transcript_target_window = "123"
    monkeypatch.setattr(
        module,
        "activate_x11_window",
        lambda window_id: restored.append(window_id) or True,
    )
    monkeypatch.setattr(
        module.QTimer,
        "singleShot",
        lambda _delay, callback: callback(),
    )
    monkeypatch.setattr(
        module,
        "paste_primary_selection",
        lambda: pasted.append(True) or True,
    )

    patched_window._paste_transcript_choice("past transcript")

    assert patched_window.presenter.copied_text == ["past transcript"]
    assert restored == ["123"]
    assert pasted == [True]
    assert patched_window._transcript_target_window is None


def test_selected_recipe_launches_in_a_new_terminal(patched_window, monkeypatch):
    recipe = Recipe(
        recipe_id="deepmetrics-health",
        title="DeepMetrics health",
        description="Inspect system health",
        keywords=("health",),
        working_directory=Path("/tmp"),
        commands=(("true",),),
    )
    launched: list[tuple[Recipe, str]] = []
    patched_window._recipe_catalog = (recipe,)
    patched_window._transcript_target_window = "123"
    monkeypatch.setattr(
        module,
        "launch_recipe_terminal",
        lambda selected, python: launched.append((selected, python)),
    )

    patched_window._launch_recipe("deepmetrics-health")

    assert launched == [(recipe, module.sys.executable)]
    assert patched_window._transcript_target_window is None
