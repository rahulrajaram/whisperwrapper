"""Recording worker used by the GUI."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ...controllers import WhisperRecordingController


class RecordingWorker(QObject):
    """Worker thread for non-blocking recording operations."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(str)
    stopped = pyqtSignal()
    status_update = pyqtSignal(str)

    def __init__(self, recording_controller: "WhisperRecordingController"):
        super().__init__()
        self.controller = recording_controller
        self.should_stop = False

    def stop(self) -> None:
        self.should_stop = True

    def run(self) -> None:
        try:
            self.controller.start()

            while self.controller.recording and not self.should_stop:
                time.sleep(0.1)

            self.status_update.emit(
                "⏳ Stopping recording and processing audio... (this may take a minute)"
            )
            transcription = self.controller.stop()
            if transcription:
                self.result.emit(transcription)
            else:
                self.error.emit("No audio data was recorded")
                self.status_update.emit("❌ No audio data was recorded")

            self.stopped.emit()
            self.finished.emit()
        except Exception as exc:  # pragma: no cover - controller handles errors
            error_msg = f"Recording error: {exc}"
            self.error.emit(error_msg)
            self.status_update.emit(error_msg)
            self.finished.emit()
