"""Whisper transcription service wrapper."""

from __future__ import annotations

import os
import tempfile
from contextlib import redirect_stderr
from typing import Optional

import pyaudio
import whisper

from ..config import WhisperRuntimeConfig


class TranscriptionService:
    """Wraps Whisper model loading and inference."""

    def __init__(self, runtime_config: WhisperRuntimeConfig):
        self.runtime_config = runtime_config
        self.device = runtime_config.device_override
        if self.device is None:
            import torch

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model(runtime_config.model_name, device=self.device)

    def transcribe_frames(
        self,
        frames,
        *,
        rate: int,
        channels: int,
        sample_format: int,
        headless: bool,
    ) -> Optional[str]:
        if not frames:
            return None

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            filename = tmp_file.name

        try:
            import wave

            wav = wave.open(filename, "wb")
            wav.setnchannels(channels)
            wav.setsampwidth(pyaudio.get_sample_size(sample_format))
            wav.setframerate(rate)
            wav.writeframes(b"".join(frames))
            wav.close()

            if headless:
                with open(os.devnull, "w") as devnull:
                    with redirect_stderr(devnull):
                        result = self.model.transcribe(filename)
            else:
                result = self.model.transcribe(filename)

            text = result.get("text", "").strip()
            return text or None
        finally:
            try:
                os.unlink(filename)
            except OSError:
                pass


__all__ = ["TranscriptionService"]
