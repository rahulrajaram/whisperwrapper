"""End-to-end CLI integration test using the real Whisper transcription stack."""

from __future__ import annotations

import math
import struct
from typing import List
from types import SimpleNamespace

from tests.helpers import ensure_whisper_module

ensure_whisper_module()


def _generate_frames(duration_sec: float = 0.5, rate: int = 16000) -> bytes:
    """Generate a simple sine wave encoded as 16-bit PCM."""
    total_samples = int(duration_sec * rate)
    frames = bytearray()
    for n in range(total_samples):
        sample = int(12000 * math.sin(2 * math.pi * 440 * n / rate))
        frames.extend(struct.pack("<h", sample))
    return bytes(frames)


def test_cli_headless_end_to_end(monkeypatch, tmp_path):
    from whisper_app.cli import WhisperCLI
    from whisper_app.controllers import recording_controller as controller_module

    synthetic_audio = _generate_frames()

    class StubAudioService:
        def __init__(self, *_, **__):
            self.input_device_index = 0

        def list_input_devices(self):
            return [SimpleNamespace(index=0, name="Stub Mic")]

        def select_default_device(self):
            return 0

        def terminate(self):
            pass

    class SyntheticSession:
        def __init__(self, audio_service, runtime_config, on_error, settings):
            self.recording = False
            self.settings = settings or SimpleNamespace(rate=16000, channels=1, format=8)
            self._frames: List[bytes] = [synthetic_audio]

        def start(self):
            self.recording = True

        def stop(self):
            self.recording = False
            return list(self._frames)

        def cleanup(self):
            pass

    monkeypatch.setattr(controller_module, "AudioInputService", lambda *a, **k: StubAudioService())
    monkeypatch.setattr(controller_module, "RecordingSession", SyntheticSession)

    monkeypatch.setattr(WhisperCLI, "_start_spinner", lambda self: None)
    monkeypatch.setattr(WhisperCLI, "_stop_spinner", lambda self: None)
    monkeypatch.setattr("builtins.input", lambda *args, **kwargs: "")

    cli = WhisperCLI(headless=True, force_configure=True, debug=False)
    result = cli.run_headless()

    assert result is None or isinstance(result, str)
