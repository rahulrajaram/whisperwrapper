#!/usr/bin/env python3
"""Tests for lightweight GUI helpers (currently RecordingWorker)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from whisper_app.gui.workers.recording import RecordingWorker


class SignalCapture:
    """Utility to capture Qt signal emissions."""

    def __init__(self):
        self.calls = []

    def handler(self, *args):
        self.calls.append(args)


class TestRecordingWorker(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = MagicMock()
        self.controller.recording = False
        self.worker = RecordingWorker(self.controller)

        # Connect signals to capture objects
        self.result_capture = SignalCapture()
        self.error_capture = SignalCapture()
        self.status_capture = SignalCapture()
        self.stopped_capture = SignalCapture()
        self.finished_capture = SignalCapture()

        self.worker.result.connect(self.result_capture.handler)
        self.worker.error.connect(self.error_capture.handler)
        self.worker.status_update.connect(self.status_capture.handler)
        self.worker.stopped.connect(self.stopped_capture.handler)
        self.worker.finished.connect(self.finished_capture.handler)

    def test_run_emits_result_when_transcription_available(self):
        self.controller.stop.return_value = "hello world"

        self.worker.run()

        self.controller.start.assert_called_once()
        self.controller.stop.assert_called_once()
        self.assertEqual(self.result_capture.calls, [("hello world",)])
        self.assertEqual(self.error_capture.calls, [])
        self.assertEqual(len(self.status_capture.calls), 1)
        self.assertEqual(self.stopped_capture.calls, [tuple()])
        self.assertEqual(self.finished_capture.calls, [tuple()])

    def test_run_emits_error_when_no_audio(self):
        self.controller.stop.return_value = None

        self.worker.run()

        self.assertEqual(self.result_capture.calls, [])
        self.assertEqual(self.error_capture.calls, [("No audio data was recorded",)])
        # Expect initial status message plus explicit error status
        self.assertEqual(
            self.status_capture.calls,
            [
                ("⏳ Stopping recording and processing audio... (this may take a minute)",),
                ("❌ No audio data was recorded",),
            ],
        )
        self.assertEqual(self.stopped_capture.calls, [tuple()])
        self.assertEqual(self.finished_capture.calls, [tuple()])

    def test_run_handles_controller_exception(self):
        self.controller.start.side_effect = RuntimeError("boom")

        self.worker.run()

        self.assertEqual(len(self.error_capture.calls), 1)
        self.assertIn("boom", self.error_capture.calls[0][0])
        self.assertEqual(self.stopped_capture.calls, [])  # stopped not emitted on fatal error
        self.assertEqual(self.finished_capture.calls, [tuple()])

    def test_stop_sets_flag(self):
        self.assertFalse(self.worker.should_stop)
        self.worker.stop()
        self.assertTrue(self.worker.should_stop)
