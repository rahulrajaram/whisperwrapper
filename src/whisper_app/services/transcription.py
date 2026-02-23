"""Whisper transcription service wrapper."""

from __future__ import annotations

import logging
import os
import tempfile
import time
import wave
from contextlib import redirect_stderr
from pathlib import Path
from typing import Dict, Optional

import pyaudio
from faster_whisper import WhisperModel

from ..config import WhisperRuntimeConfig
from ..replacements import apply_replacements, load_replacements

logger = logging.getLogger(__name__)

GLOBAL_VOCABULARY_PATH = Path.home() / ".whisper" / "vocabulary.txt"
GLOBAL_REPLACEMENTS_PATH = Path.home() / ".whisper" / "replacements.txt"


class TranscriptionService:
    """Wraps Whisper model loading and inference."""

    def __init__(self, runtime_config: WhisperRuntimeConfig):
        self.runtime_config = runtime_config
        self.device = runtime_config.device_override
        if self.device is None:
            import torch

            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        compute_type = "float16" if self.device == "cuda" else "int8"

        logger.info(
            f"Loading Whisper model '{runtime_config.model_name}' on device: {self.device} "
            f"(compute_type={compute_type})"
        )

        t0 = time.monotonic()
        try:
            self.model = WhisperModel(
                runtime_config.model_name, device=self.device, compute_type=compute_type
            )
        except Exception:
            if self.device == "cuda":
                logger.warning("CUDA model load failed, falling back to CPU")
                self.device = "cpu"
                self.model = WhisperModel(
                    runtime_config.model_name, device="cpu", compute_type="int8"
                )
            else:
                raise
        load_time = time.monotonic() - t0
        logger.info("Model loaded in %.1fs on %s", load_time, self.device)

        self._vocab_prompt: Optional[str] = None
        self._vocab_mtime: float = 0.0
        self._replacements_cache: Dict[str, str] = {}
        self._replacements_mtime: float = 0.0

    def _get_vocabulary_prompt(self) -> Optional[str]:
        """Return cached vocabulary prompt, reloading only when the file changes."""
        try:
            if not GLOBAL_VOCABULARY_PATH.exists():
                if self._vocab_prompt is not None:
                    logger.info("Vocabulary file removed, clearing prompt")
                    self._vocab_prompt = None
                    self._vocab_mtime = 0.0
                return None
            mtime = GLOBAL_VOCABULARY_PATH.stat().st_mtime
            if mtime == self._vocab_mtime:
                return self._vocab_prompt
            text = GLOBAL_VOCABULARY_PATH.read_text(encoding="utf-8").strip()
            if not text:
                self._vocab_prompt = None
                self._vocab_mtime = mtime
                return None
            terms = [t.strip() for t in text.splitlines() if t.strip()]
            self._vocab_prompt = ", ".join(terms)
            self._vocab_mtime = mtime
            logger.info("Loaded %d vocabulary terms from %s", len(terms), GLOBAL_VOCABULARY_PATH)
            return self._vocab_prompt
        except Exception:
            logger.warning("Failed to read vocabulary file", exc_info=True)
            return self._vocab_prompt  # Return last known good value

    def _get_replacements(self) -> Dict[str, str]:
        """Return cached replacements, reloading only when the file changes."""
        try:
            if not GLOBAL_REPLACEMENTS_PATH.exists():
                if self._replacements_cache:
                    logger.info("Replacements file removed, clearing cache")
                    self._replacements_cache = {}
                    self._replacements_mtime = 0.0
                return {}
            mtime = GLOBAL_REPLACEMENTS_PATH.stat().st_mtime
            if mtime == self._replacements_mtime:
                return self._replacements_cache
            self._replacements_cache = load_replacements()
            self._replacements_mtime = mtime
            logger.info("Loaded %d replacement(s) from %s", len(self._replacements_cache), GLOBAL_REPLACEMENTS_PATH)
            return self._replacements_cache
        except Exception:
            logger.warning("Failed to read replacements file", exc_info=True)
            return self._replacements_cache

    def cleanup(self) -> None:
        """Release the Whisper model and free GPU memory."""
        if hasattr(self, "model"):
            del self.model
            self.model = None  # type: ignore[assignment]
            logger.debug("Whisper model deleted")

        if self.device == "cuda":
            try:
                import torch.cuda
                torch.cuda.empty_cache()
                logger.debug("CUDA cache cleared")
            except Exception:
                pass

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
            audio_data = b"".join(frames)
            sample_width = pyaudio.get_sample_size(sample_format)
            audio_duration = len(audio_data) / (rate * channels * sample_width)

            wav = wave.open(filename, "wb")
            wav.setnchannels(channels)
            wav.setsampwidth(sample_width)
            wav.setframerate(rate)
            wav.writeframes(audio_data)
            wav.close()

            transcribe_kwargs = dict(
                beam_size=5, initial_prompt=self._get_vocabulary_prompt()
            )

            t0 = time.monotonic()
            if headless:
                with open(os.devnull, "w") as devnull:
                    with redirect_stderr(devnull):
                        segments, _info = self.model.transcribe(
                            filename, **transcribe_kwargs
                        )
            else:
                segments, _info = self.model.transcribe(
                    filename, **transcribe_kwargs
                )

            text = " ".join(segment.text for segment in segments).strip()

            replacements = self._get_replacements()
            if replacements:
                text = apply_replacements(text, replacements)

            inference_time = time.monotonic() - t0

            realtime_factor = audio_duration / inference_time if inference_time > 0 else 0
            logger.info(
                "Transcription: %.1fs audio → %.1fs inference (%.1fx realtime) on %s",
                audio_duration, inference_time, realtime_factor, self.device,
            )

            del segments, _info

            import gc
            gc.collect()

            return text or None
        finally:
            try:
                os.unlink(filename)
            except OSError:
                pass


__all__ = ["TranscriptionService"]
