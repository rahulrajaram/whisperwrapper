"""Tests for the WhisperRecordingController logic."""

from __future__ import annotations

from types import SimpleNamespace
from typing import List, Optional

import pytest

from whisper_app.controllers import recording_controller as module
from whisper_app.controllers.recording_controller import (
    RecordingEventCallbacks,
    WhisperRecordingController,
)


class StubAudioService:
    def __init__(self, *_, **__):
        self.input_device_index = 0


class StubSession:
    def __init__(self, *_, **__):
        self.recording = False
        self.settings = SimpleNamespace(rate=16000, channels=1, format=1)
        self.frames_to_return: List[bytes] = [b"audio"]
        self.cleaned = False

    def start(self):
        self.recording = True

    def stop(self):
        frames = list(self.frames_to_return)
        self.frames_to_return = []
        self.recording = False
        return frames

    def cleanup(self):
        self.cleaned = True


class StubTranscription:
    def __init__(self, *_):
        self.result: Optional[str] = "hello world"
        self.calls = []

    def transcribe_frames(self, frames, **kwargs):
        self.calls.append((frames, kwargs))
        return self.result


class StubLifecycleAdapter:
    def __init__(self):
        self.events = []

    def before_recording_start(self):
        self.events.append("starting")

    def after_recording_stop(self):
        self.events.append("stopped")


@pytest.fixture(autouse=True)
def patch_recording_dependencies(monkeypatch):
    monkeypatch.setattr(module, "AudioInputService", lambda *args, **kwargs: StubAudioService())
    monkeypatch.setattr(module, "RecordingSession", lambda *args, **kwargs: StubSession())
    monkeypatch.setattr(module, "TranscriptionService", lambda *args, **kwargs: StubTranscription())
    monkeypatch.setattr(
        module,
        "CommandRecordingLifecycleAdapter",
        lambda *args, **kwargs: StubLifecycleAdapter(),
    )


def test_controller_start_stop_triggers_callbacks():
    events = []
    lifecycle = StubLifecycleAdapter()

    callbacks = RecordingEventCallbacks(
        on_start=lambda: events.append("start"),
        on_stop=lambda: events.append("stop"),
        on_result=lambda text: events.append(f"result:{text}"),
    )

    controller = WhisperRecordingController(callbacks=callbacks, lifecycle_adapter=lifecycle)
    controller.start()
    assert controller.recording

    controller.stop()
    assert events == ["start", "stop", "result:hello world"]
    assert lifecycle.events == ["starting", "stopped"]
    assert controller.last_result == "hello world"


def test_controller_stop_without_frames_returns_none():
    lifecycle = StubLifecycleAdapter()
    callbacks = RecordingEventCallbacks(on_stop=lambda: None, on_result=lambda text: None)
    controller = WhisperRecordingController(callbacks=callbacks, lifecycle_adapter=lifecycle)
    controller.session.frames_to_return = []
    controller.start()
    result = controller.stop()
    assert result is None
    assert controller.last_result is None
    assert lifecycle.events == ["starting", "stopped"]


def test_toggle_switches_state():
    controller = WhisperRecordingController()
    assert controller.toggle() is None  # starts recording
    controller.session.frames_to_return = [b"x"]
    result = controller.toggle()
    assert result == "hello world"
    assert not controller.recording


def test_handle_error_records_message():
    errors = []
    controller = WhisperRecordingController(
        callbacks=RecordingEventCallbacks(on_error=errors.append)
    )
    controller._handle_error(RuntimeError("boom"))
    assert controller.last_error == "boom"
    assert errors == ["boom"]


def test_cleanup_delegates_to_session():
    lifecycle = StubLifecycleAdapter()
    controller = WhisperRecordingController(lifecycle_adapter=lifecycle)
    controller.cleanup()
    assert controller.session.cleaned
    assert lifecycle.events == ["stopped"]


def test_failed_recording_start_releases_owned_media():
    lifecycle = StubLifecycleAdapter()
    controller = WhisperRecordingController(lifecycle_adapter=lifecycle)
    controller.session.start = lambda: None

    controller.start()

    assert not controller.recording
    assert lifecycle.events == ["starting", "stopped"]
