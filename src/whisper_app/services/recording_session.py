"""Audio recording session abstraction."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, List, Optional

import pyaudio

from ..config import WhisperRuntimeConfig
from .audio_input import AudioInputService


@dataclass
class RecordingSettings:
    chunk: int = 4096
    format: int = pyaudio.paInt16
    channels: int = 1
    rate: int = 16000


class RecordingSession:
    """Handles streaming audio frames from the selected microphone."""

    def __init__(
        self,
        audio_service: AudioInputService,
        runtime_config: WhisperRuntimeConfig,
        on_error: Optional[Callable[[Exception], None]] = None,
        settings: Optional[RecordingSettings] = None,
    ) -> None:
        self.audio_service = audio_service
        self.runtime_config = runtime_config
        self.settings = settings or RecordingSettings()
        self._frames: List[bytes] = []
        self._recording = False
        self._stream: Optional[pyaudio.Stream] = None
        self._thread: Optional[threading.Thread] = None
        self._on_error = on_error

    @property
    def recording(self) -> bool:
        return self._recording

    @property
    def frames(self) -> List[bytes]:
        return self._frames

    def start(self) -> None:
        if self._recording:
            return

        self._frames = []
        self._recording = True
        try:
            self._stream = self.audio_service.audio.open(
                format=self.settings.format,
                channels=self.settings.channels,
                rate=self.settings.rate,
                input=True,
                frames_per_buffer=self.settings.chunk,
                input_device_index=self.audio_service.input_device_index,
                start=False,
            )
            self._stream.start_stream()
        except Exception as exc:
            self._recording = False
            self._stream = None
            if self._on_error:
                self._on_error(exc)
            return

        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self) -> List[bytes]:
        if not self._recording:
            return []

        self._recording = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._stream is not None:
            try:
                self._stream.stop_stream()
            except Exception:
                pass
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        frames, self._frames = self._frames, []
        return frames

    def cleanup(self) -> None:
        self.stop()
        self.audio_service.terminate()

    def _capture_loop(self) -> None:
        if not self._stream:
            return
        while self._recording and self._stream.is_active():
            try:
                data = self._stream.read(self.settings.chunk, exception_on_overflow=False)
                if data:
                    self._frames.append(data)
            except Exception as exc:
                self._recording = False
                if self._on_error:
                    self._on_error(exc)
                break


__all__ = ["RecordingSession", "RecordingSettings"]
