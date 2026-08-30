"""Tests for recording and transcription services with scoped stubbing."""

from __future__ import annotations

import math
import os
import struct
import sys
from unittest.mock import MagicMock

import numpy as np
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
    original = sys.modules.get("faster_whisper")
    transcription = sys.modules.get("whisper_app.services.transcription")
    original_whisper_model = getattr(transcription, "WhisperModel", None) if transcription else None
    stub = install_whisper_stub()
    log_whisper_event("faster-whisper stub installed for tests/test_services.py")
    yield stub
    if original is None:
        sys.modules.pop("faster_whisper", None)
    else:
        sys.modules["faster_whisper"] = original
    if transcription is not None and original_whisper_model is not None:
        setattr(transcription, "WhisperModel", original_whisper_model)
    log_whisper_event("faster-whisper stub removed for tests/test_services.py")


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

        def open_input_stream(self, **kwargs):
            return self.audio.open(**kwargs)

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


def test_safe_input_device_index_falls_back_when_named_device_is_missing(tmp_path, monkeypatch):
    """A missing stable preference must fall back to the system route."""
    from whisper_app.services.audio_input import (
        PORTAUDIO_ROUTE_PREFIX,
        AudioInputService,
    )

    class FakeDeviceInfo:
        def __init__(self, idx, channels):
            self._index = idx
            self._channels = channels

        def get(self, key, default=None):
            return {
                "name": f"Device {self._index}",
                "maxInputChannels": self._channels,
                "index": self._index,
            }.get(key, default)

    class FakeAudio:
        def get_device_count(self):
            return 3

        def get_device_info_by_index(self, idx):
            # Only index 1 offers input channels; 0 and 2 are output-only.
            channels = 2 if idx == 1 else 0
            return FakeDeviceInfo(idx, channels)

        def get_default_input_device_info(self):
            return FakeDeviceInfo(1, 2)

    paths = __import__("whisper_app.config", fromlist=["WhisperPaths"]).WhisperPaths(
        base_dir=tmp_path / "whisper"
    )
    service = AudioInputService.__new__(AudioInputService)
    service._headless = True
    service._debug = False
    service._paths = paths
    service._audio = FakeAudio()
    service._input_route = f"{PORTAUDIO_ROUTE_PREFIX}Unplugged USB microphone"
    monkeypatch.setenv("PULSE_SOURCE", "stale-source")

    assert service.safe_input_device_index() is None
    assert service.input_route == "portaudio:Unplugged USB microphone"
    assert "PULSE_SOURCE" not in os.environ

    service._input_route = f"{PORTAUDIO_ROUTE_PREFIX}Device 1"
    assert service.safe_input_device_index() == 1


def test_parse_pipewire_sources_includes_tonor_and_excludes_monitors():
    import json

    from whisper_app.services.audio_input import parse_pipewire_sources

    tonor_name = (
        "alsa_input.usb-C-Media_Electronics_Inc." "_TONOR_TC-777_Audio_Device-00.mono-fallback"
    )
    payload = json.dumps(
        [
            {
                "name": "alsa_output.card.monitor",
                "description": "Speaker monitor",
                "properties": {"media.class": "Audio/Sink"},
            },
            {
                "name": tonor_name,
                "description": "TONOR TC-777 Audio Device Mono",
                "properties": {"media.class": "Audio/Source"},
            },
        ]
    )

    choices = parse_pipewire_sources(payload)

    assert [choice.label for choice in choices] == ["TONOR TC-777 Audio Device Mono"]
    assert choices[0].key == f"pipewire:{tonor_name}"
    assert choices[0].source_name == tonor_name


def test_pipewire_route_uses_pulse_device_and_selected_source(monkeypatch):
    from whisper_app.services.audio_input import AudioInputChoice, AudioInputService

    tonor_name = "alsa_input.usb-TONOR.mono-fallback"
    service = AudioInputService.__new__(AudioInputService)
    service._input_route = f"pipewire:{tonor_name}"
    service._discover_pipewire_sources = lambda: (
        AudioInputChoice(
            key=f"pipewire:{tonor_name}",
            label="TONOR microphone",
            source_name=tonor_name,
        ),
    )
    service._find_portaudio_device_index = lambda name: 7 if name == "pulse" else None
    monkeypatch.delenv("PULSE_SOURCE", raising=False)

    assert service.safe_input_device_index() == 7
    assert os.environ["PULSE_SOURCE"] == tonor_name


def test_input_choices_use_pipewire_as_the_authoritative_inventory():
    from whisper_app.services.audio_input import (
        AudioDeviceInfo,
        AudioInputChoice,
        AudioInputService,
    )

    tonor = AudioInputChoice(
        key="pipewire:tonor",
        label="TONOR TC-777",
        source_name="tonor",
    )
    service = AudioInputService.__new__(AudioInputService)
    service._discover_pipewire_sources = lambda: (tonor,)
    service.list_input_devices = lambda: [
        AudioDeviceInfo(index=1, name="pulse", max_input_channels=32),
        AudioDeviceInfo(index=2, name="default", max_input_channels=32),
        AudioDeviceInfo(index=3, name="DEPSTECH", max_input_channels=1),
    ]

    choices = service.list_input_choices()

    assert [choice.key for choice in choices] == [
        "system",
        "pipewire:tonor",
    ]


def test_input_choices_use_physical_direct_devices_when_pipewire_is_unavailable():
    from whisper_app.services.audio_input import AudioDeviceInfo, AudioInputService

    service = AudioInputService.__new__(AudioInputService)
    service._discover_pipewire_sources = lambda: None
    service.list_input_devices = lambda: [
        AudioDeviceInfo(index=1, name="pulse", max_input_channels=32),
        AudioDeviceInfo(index=2, name="sysdefault", max_input_channels=32),
        AudioDeviceInfo(
            index=3,
            name="DEPSTECH webcam: USB Audio (hw:2,0)",
            max_input_channels=1,
        ),
    ]

    choices = service.list_input_choices()

    assert [choice.key for choice in choices] == [
        "system",
        "portaudio:DEPSTECH webcam: USB Audio (hw:2,0)",
    ]


def test_open_input_stream_reinitializes_after_device_unavailable(tmp_path):
    from whisper_app.services.audio_input import AudioInputService

    class WorkingAudio:
        def open(self, **kwargs):
            return ("stream", kwargs)

    class StaleAudio:
        def open(self, **kwargs):
            raise OSError(-9985, "Device unavailable")

        def terminate(self):
            pass

    paths = __import__("whisper_app.config", fromlist=["WhisperPaths"]).WhisperPaths(
        base_dir=tmp_path / "whisper"
    )
    service = AudioInputService.__new__(AudioInputService)
    service._headless = True
    service._debug = False
    service._paths = paths
    service._audio = StaleAudio()
    service._input_route = "system"
    service._init_audio = lambda: WorkingAudio()

    stream, kwargs = service.open_input_stream(input=True, channels=1)

    assert stream == "stream"
    assert kwargs["input_device_index"] is None


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


def test_transcription_skips_whisper_inference_when_no_speech_is_detected(
    whisper_stub, monkeypatch
):
    from whisper_app.config import WhisperRuntimeConfig
    from whisper_app.services import transcription as module

    config = WhisperRuntimeConfig(model_name="tiny", headless=True)
    service = module.TranscriptionService(config)
    transcribe = MagicMock(side_effect=AssertionError("Whisper inference must be skipped"))
    service.model.transcribe = transcribe
    monkeypatch.setattr(module, "get_speech_timestamps", lambda *args, **kwargs: [])

    text = service.transcribe_frames(
        [b"\x00\x00" * 1600],
        rate=16000,
        channels=1,
        sample_format=8,
        headless=True,
    )

    assert text is None
    transcribe.assert_not_called()


def test_transcription_sends_only_vad_detected_speech_to_whisper(whisper_stub, monkeypatch):
    from whisper_app.config import WhisperRuntimeConfig
    from whisper_app.services import transcription as module

    config = WhisperRuntimeConfig(model_name="tiny", headless=True)
    service = module.TranscriptionService(config)
    original_transcribe = service.model.transcribe
    transcribe = MagicMock(side_effect=original_transcribe)
    service.model.transcribe = transcribe
    monkeypatch.setattr(
        module,
        "get_speech_timestamps",
        lambda *args, **kwargs: [{"start": 800, "end": 2400}],
    )

    text = service.transcribe_frames(
        [sine_wave(duration_sec=0.2)],
        rate=16000,
        channels=1,
        sample_format=8,
        headless=True,
    )

    assert text is not None
    speech_audio = transcribe.call_args.args[0]
    assert isinstance(speech_audio, np.ndarray)
    assert len(speech_audio) == 1600


def test_speech_gate_accepts_faster_whisper_1_0_collected_audio_shape(
    whisper_stub, monkeypatch, tmp_path
):
    import wave

    from whisper_app.services import transcription as module

    filename = tmp_path / "speech.wav"
    with wave.open(str(filename), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(sine_wave(duration_sec=0.2))

    legacy_collected_audio = np.ones(1600, dtype=np.float32)
    monkeypatch.setattr(
        module,
        "get_speech_timestamps",
        lambda *args, **kwargs: [{"start": 0, "end": 1600}],
    )
    monkeypatch.setattr(
        module,
        "collect_chunks",
        lambda *args, **kwargs: legacy_collected_audio,
    )

    speech_audio = module._speech_audio(str(filename))

    assert speech_audio is legacy_collected_audio
