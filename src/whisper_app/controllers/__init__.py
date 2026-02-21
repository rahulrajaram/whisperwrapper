"""Controller abstractions used by GUI/CLI/daemons."""

from .recording_controller import RecordingController, RecordingEventCallbacks, WhisperRecordingController

__all__ = [
    "RecordingController",
    "RecordingEventCallbacks",
    "WhisperRecordingController",
]
