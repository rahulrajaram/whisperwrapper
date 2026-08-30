"""Recording controller abstraction for UI + automation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from ..config import WhisperRuntimeConfig
from ..services import (
    AudioInputService,
    CommandRecordingLifecycleAdapter,
    RecordingLifecycleAdapter,
    RecordingSession,
    RecordingSettings,
    TranscriptionService,
)

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
        lifecycle_adapter: Optional[RecordingLifecycleAdapter] = None,
    ) -> None:
        self.runtime_config = runtime_config or WhisperRuntimeConfig()
        self.callbacks = callbacks or RecordingEventCallbacks()
        self.lifecycle_adapter = lifecycle_adapter or CommandRecordingLifecycleAdapter(
            self.runtime_config.recording_lifecycle
        )
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
        self.lifecycle_adapter.before_recording_start()
        self.session.start()
        if not self.session.recording:
            self.lifecycle_adapter.after_recording_stop()
            return
        if self.session.recording and self.callbacks.on_start:
            self.callbacks.on_start()

    def stop(self) -> Optional[str]:
        try:
            frames = self.session.stop()
        finally:
            self.lifecycle_adapter.after_recording_stop()
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
        try:
            self.session.cleanup()
        finally:
            self.lifecycle_adapter.after_recording_stop()

    def _handle_error(self, exc: Exception) -> None:
        self.lifecycle_adapter.after_recording_stop()
        self._last_error = str(exc)
        if self.callbacks.on_error:
            self.callbacks.on_error(str(exc))


__all__ = [
    "RecordingController",
    "RecordingEventCallbacks",
    "WhisperRecordingController",
]
