"""Tests for recording and transcription services with scoped stubbing."""

from __future__ import annotations

import math
import struct
import sys
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

import pytest

from tests.helpers import install_whisper_stub, log_whisper_event


def sine_wave(duration_sec: float = 0.2, rate: int = 16000) -> bytes:
    total_samples = int(duration_sec * rate)
    frames = bytearray()
    for n in range(total_samples):
        sample = int(8000 * math.sin(2 * math.pi * 440 * n / rate))
        frames.extend(struct.pack("<h", sample))
    return bytes(frames)


@pytest.fixture
def whisper_stub():
    original = sys.modules.get("whisper")
    transcription = sys.modules.get("whisper_app.services.transcription")
    original_transcription_whisper = getattr(transcription, "whisper", None) if transcription else None
    stub = install_whisper_stub()
    log_whisper_event("whisper stub installed for tests/test_services.py")
    yield stub
    if original is None:
        sys.modules.pop("whisper", None)
    else:
        sys.modules["whisper"] = original
    if transcription is not None:
        setattr(transcription, "whisper", original_transcription_whisper)
    log_whisper_event("whisper stub removed for tests/test_services.py")


def test_recording_session_start_stop(monkeypatch):
    from whisper_app.services.recording_session import RecordingSession, RecordingSettings

    class FakeStream:
        def __init__(self):
            self.started = False
            self.stopped = False
            self.closed = False
            self.reads = 0

        def start_stream(self):
            self.started = True

        def stop_stream(self):
            self.stopped = True

        def close(self):
            self.closed = True

        def is_active(self):
            return not self.stopped and self.reads < 2

        def read(self, chunk, exception_on_overflow=False):
            self.reads += 1
            return sine_wave(duration_sec=0.01)

    class FakeAudio:
        def __init__(self):
            self.stream = FakeStream()

        def open(self, **kwargs):
            return self.stream

    class FakeAudioService:
        def __init__(self):
            self.audio = FakeAudio()
            self.input_device_index = 0

        def terminate(self):
            pass

    session = RecordingSession(
        audio_service=FakeAudioService(),
        runtime_config=MagicMock(),
        on_error=None,
        settings=RecordingSettings(),
    )

    session.start()
    frames = session.stop()

    assert frames
    session.cleanup()


def test_transcription_service_with_stub(whisper_stub, tmp_path):
    from whisper_app.config import WhisperRuntimeConfig
    from whisper_app.services.transcription import TranscriptionService

    config = WhisperRuntimeConfig(model_name="tiny", headless=True)
    service = TranscriptionService(config)

    frames = sine_wave(duration_sec=0.1)
    text = service.transcribe_frames(
        [frames],
        rate=16000,
        channels=1,
        sample_format=8,
        headless=True,
    )
    assert text is not None
