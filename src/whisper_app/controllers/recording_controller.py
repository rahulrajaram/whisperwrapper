"""Recording controller abstraction for UI + automation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from ..config import WhisperRuntimeConfig
from ..services import AudioInputService, RecordingSession, RecordingSettings, TranscriptionService


RecordingCallback = Callable[[], None]
ResultCallback = Callable[[str], None]
ErrorCallback = Callable[[str], None]


@dataclass
class RecordingEventCallbacks:
    on_start: Optional[RecordingCallback] = None
    on_stop: Optional[RecordingCallback] = None
    on_result: Optional[ResultCallback] = None
    on_error: Optional[ErrorCallback] = None


class RecordingController:
    """Interface for controlling audio recording lifecycle."""

    def start(self) -> None:  # pragma: no cover - interface doc
        raise NotImplementedError

    def stop(self) -> Optional[str]:  # pragma: no cover - interface doc
        raise NotImplementedError

    def toggle(self) -> Optional[str]:  # pragma: no cover
        raise NotImplementedError

    def cleanup(self) -> None:  # pragma: no cover
        raise NotImplementedError


class WhisperRecordingController(RecordingController):
    """Concrete controller that wires audio services + Whisper transcription."""

    def __init__(
        self,
        runtime_config: Optional[WhisperRuntimeConfig] = None,
        callbacks: Optional[RecordingEventCallbacks] = None,
        recording_settings: Optional[RecordingSettings] = None,
    ) -> None:
        self.runtime_config = runtime_config or WhisperRuntimeConfig()
        self.callbacks = callbacks or RecordingEventCallbacks()
        self.audio_service = AudioInputService(
            headless=self.runtime_config.headless,
            paths=self.runtime_config.paths,
            debug=self.runtime_config.debug,
        )
        self.session = RecordingSession(
            audio_service=self.audio_service,
            runtime_config=self.runtime_config,
            on_error=self._handle_error,
            settings=recording_settings,
        )
        self.transcription = TranscriptionService(self.runtime_config)
        self._last_error: Optional[str] = None
        self._last_result: Optional[str] = None

    @property
    def recording(self) -> bool:
        return self.session.recording

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @property
    def last_result(self) -> Optional[str]:
        return self._last_result

    def start(self) -> None:
        if self.session.recording:
            return
        self.session.start()
        if self.session.recording and self.callbacks.on_start:
            self.callbacks.on_start()

    def stop(self) -> Optional[str]:
        frames = self.session.stop()
        if not frames:
            return None

        if self.callbacks.on_stop:
            self.callbacks.on_stop()

        text = self.transcription.transcribe_frames(
            frames,
            rate=self.session.settings.rate,
            channels=self.session.settings.channels,
            sample_format=self.session.settings.format,
            headless=self.runtime_config.headless,
        )
        self._last_result = text
        if text and self.callbacks.on_result:
            self.callbacks.on_result(text)
        return text

    def toggle(self) -> Optional[str]:
        if self.session.recording:
            return self.stop()
        self.start()
        return None

    def cleanup(self) -> None:
        self.session.cleanup()

    def _handle_error(self, exc: Exception) -> None:
        self._last_error = str(exc)
        if self.callbacks.on_error:
            self.callbacks.on_error(str(exc))


__all__ = [
    "RecordingController",
    "RecordingEventCallbacks",
    "WhisperRecordingController",
]
