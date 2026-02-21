"""Unit tests for the WhisperPresenter view-model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from unittest.mock import MagicMock

import pytest

from whisper_app.gui import presenter as presenter_module
from whisper_app.gui.presenter import WhisperPresenter
from whisper_app.gui.projects import ProjectManager


class DummySignal:
    """Lightweight stand-in for pyqtSignal used by fake workers/threads."""

    def __init__(self):
        self._callbacks: List = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for callback in list(self._callbacks):
            callback(*args, **kwargs)


class FakeThread:
    """Minimal QThread replacement that synchronously invokes callbacks."""

    def __init__(self):
        self.started = DummySignal()
        self._running = False

    def start(self):
        self._running = True
        self.started.emit()

    def isRunning(self):
        return self._running

    def quit(self):
        self._running = False

    def wait(self):
        pass


class FakeRecordingWorker:
    """Recording worker stub that immediately emits a transcription result."""

    def __init__(self, controller):
        self.controller = controller
        self.finished = DummySignal()
        self.result = DummySignal()
        self.error = DummySignal()
        self.status_update = DummySignal()
        self._stopped = False

    def moveToThread(self, thread):
        self.thread = thread

    def run(self):
        self.status_update.emit("🎤 Recording...")
        try:
            self.controller.start()
            transcription = self.controller.stop()
            if transcription:
                self.result.emit(transcription)
            else:
                self.error.emit("No audio data was recorded")
        finally:
            self.finished.emit()

    def stop(self):
        self._stopped = True


class FakeCodexWorker:
    """Codex worker stub that transforms text synchronously."""

    def __init__(self, text: str, row_index: int):
        self.text = text
        self.row_index = row_index
        self.finished = DummySignal()
        self.result = DummySignal()
        self.error = DummySignal()

    def moveToThread(self, thread):
        self.thread = thread

    def run(self):
        self.result.emit(f"{self.text} ✨", self.row_index)
        self.finished.emit()


@dataclass
class DummyController:
    """Simplified recording controller for presenter tests."""

    transcription: str = "hello world"
    started: bool = False
    stopped: bool = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True
        return self.transcription

    def cleanup(self):
        pass


@dataclass
class InMemoryStorage:
    """Storage replacement that keeps history in memory."""

    data: List[dict] = field(default_factory=list)

    def load_history(self):
        return list(self.data)

    def save_history(self, history):
        self.data = [dict(item) for item in history]


@pytest.fixture(autouse=True)
def patch_presenter_dependencies(monkeypatch):
    monkeypatch.setattr(presenter_module, "QThread", FakeThread)
    monkeypatch.setattr(presenter_module, "RecordingWorker", FakeRecordingWorker)
    monkeypatch.setattr(presenter_module, "CodexWorker", FakeCodexWorker)
    yield


@pytest.fixture
def presenter_setup(tmp_path):
    controller = DummyController()
    storage = InMemoryStorage()
    project_manager = ProjectManager(MagicMock(base_dir=tmp_path))
    presenter = WhisperPresenter(controller, storage, project_manager)
    presenter._copy_text_to_clipboard = MagicMock(return_value=True)
    presenter._auto_paste = MagicMock()
    return presenter, controller, storage


def test_start_recording_updates_history_and_emits_signals(presenter_setup):
    presenter, controller, storage = presenter_setup
    events: List[str] = []
    presenter.recording_started.connect(lambda: events.append("started"))
    presenter.recording_finished.connect(lambda: events.append("finished"))
    presenter.transcription_ready.connect(lambda text: events.append(f"text:{text}"))
    presenter.history_changed.connect(lambda: events.append("history"))

    assert presenter.start_recording() is True
    assert controller.started and controller.stopped
    assert presenter.history[0]["text"] == "hello world"
    assert storage.data[0]["text"] == "hello world"
    assert events[0] == "started"
    assert events[-1] == "finished"
    assert "text:hello world" in events
    assert "history" in events


def test_stop_recording_emits_status_when_worker_active(presenter_setup):
    presenter, controller, _ = presenter_setup
    presenter.is_recording = True
    presenter._recording_worker = MagicMock()
    messages: List[str] = []
    presenter.status_message.connect(messages.append)

    presenter.stop_recording()

    presenter._recording_worker.stop.assert_called_once()
    assert messages[-1] == "⏳ Processing transcription..."


def test_toggle_protection_and_delete_history(presenter_setup):
    presenter, _, storage = presenter_setup
    presenter.history = [
        {"timestamp": "t1", "text": "alpha", "protected": False},
        {"timestamp": "t2", "text": "beta", "protected": False},
    ]
    storage.save_history(presenter.history)

    presenter.toggle_protection(0)
    assert presenter.history[0]["protected"] is True

    presenter.delete_history_item(0)
    assert len(presenter.history) == 1
    assert presenter.history[0]["text"] == "beta"


def test_clear_history_retains_protected_items(presenter_setup):
    presenter, _, _ = presenter_setup
    current_project = presenter.project_manager.current_project
    presenter.history = [
        {"timestamp": "t1", "text": "alpha", "protected": True, "project_id": current_project.id},
        {"timestamp": "t2", "text": "beta", "protected": False, "project_id": current_project.id},
    ]
    presenter.clear_history()
    # Should retain only the protected item from the current project
    assert len(presenter.history) == 1
    assert presenter.history[0]["text"] == "alpha"
    assert presenter.history[0]["protected"] is True


def test_copy_to_clipboard_uses_helper(presenter_setup):
    presenter, _, _ = presenter_setup
    presenter.history = [{"timestamp": "t1", "text": "alpha", "protected": False}]
    presenter._copy_text_to_clipboard.reset_mock()

    presenter.copy_to_clipboard(0)

    presenter._copy_text_to_clipboard.assert_called_once_with("alpha")


def test_process_with_codex_updates_selected_row(presenter_setup):
    presenter, _, storage = presenter_setup
    presenter.history = [
        {"timestamp": "t1", "text": "latest", "protected": False},
        {"timestamp": "t2", "text": "older", "protected": False},
    ]
    presenter.selected_row = 1
    presenter.history_changed.connect(lambda: None)  # ensure signal wiring

    presenter.process_with_codex()

    assert presenter.history[1]["text"].endswith("✨")
    assert storage.data[1]["text"].endswith("✨")


def test_process_with_codex_without_history_emits_status(presenter_setup):
    presenter, _, _ = presenter_setup
    messages: List[str] = []
    presenter.status_message.connect(messages.append)

    presenter.process_with_codex()

    assert messages[-1] == "❌ No transcriptions to process"


def test_toggle_row_selection_returns_expected_row(presenter_setup):
    presenter, _, _ = presenter_setup
    assert presenter.toggle_row_selection(0) == 0
    assert presenter.toggle_row_selection(0) is None
