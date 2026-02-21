#!/usr/bin/env python3
"""Updated unit tests for the refactored WhisperCLI."""

from __future__ import annotations

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from whisper_app.cli import WhisperCLI


class WhisperCLITestBase(unittest.TestCase):
    """Provides shared patches for WhisperCLI tests."""

    def setUp(self) -> None:
        self.runtime_config = Mock(headless=True, debug=False)
        self.audio_service = MagicMock()
        self.audio_service.input_device_index = 0
        self.controller = MagicMock()
        self.controller.audio_service = self.audio_service

        runtime_patch = patch('whisper_app.cli.WhisperRuntimeConfig', return_value=self.runtime_config)
        controller_patch = patch('whisper_app.cli.WhisperRecordingController', return_value=self.controller)

        self.runtime_patch = runtime_patch.start()
        self.controller_patch = controller_patch.start()
        self.addCleanup(runtime_patch.stop)
        self.addCleanup(controller_patch.stop)


class TestWhisperCLIInitialization(WhisperCLITestBase):
    def test_initialization_uses_runtime_config(self):
        WhisperCLI(headless=True, debug=True)
        self.runtime_patch.assert_called_once_with(headless=True, debug=True)
        self.controller_patch.assert_called_once()

    def test_force_configure_invokes_microphone_selection(self):
        self.audio_service.input_device_index = None
        with patch.object(WhisperCLI, '_select_microphone') as mock_select:
            WhisperCLI(headless=True, force_configure=True)
        mock_select.assert_called_once()

    def test_missing_device_index_triggers_microphone_selection(self):
        self.audio_service.input_device_index = None
        with patch.object(WhisperCLI, '_select_microphone') as mock_select:
            WhisperCLI(headless=True, debug=False)
        mock_select.assert_called_once()


class TestWhisperCLIRecording(WhisperCLITestBase):
    def test_start_recording_delegates_to_controller(self):
        cli = WhisperCLI(headless=True, debug=False)
        cli.start_recording()
        self.controller.start.assert_called_once()

    def test_stop_recording_writes_fifo_when_transcript_available(self):
        cli = WhisperCLI(headless=True, debug=False)
        self.controller.stop.return_value = "hello world"
        with tempfile.TemporaryDirectory() as tmpdir:
            fifo_path = os.path.join(tmpdir, 'fifo.txt')
            with patch.dict(os.environ, {'WHISPER_TRANSCRIPT_FIFO': fifo_path}, clear=True):
                cli.stop_recording()
                with open(fifo_path, 'r') as fifo:
                    self.assertEqual(fifo.read(), "hello world")

    def test_stop_recording_skips_fifo_when_no_transcript(self):
        cli = WhisperCLI(headless=True, debug=False)
        self.controller.stop.return_value = None
        with tempfile.TemporaryDirectory() as tmpdir:
            fifo_path = os.path.join(tmpdir, 'fifo.txt')
            with patch.dict(os.environ, {'WHISPER_TRANSCRIPT_FIFO': fifo_path}, clear=True):
                cli.stop_recording()
                self.assertFalse(os.path.exists(fifo_path))

    def test_cleanup_closes_controller(self):
        cli = WhisperCLI(headless=True, debug=False)
        cli.cleanup()
        self.controller.cleanup.assert_called_once()


class TestWhisperCLIMicrophoneSelection(WhisperCLITestBase):
    def test_select_microphone_headless_uses_default(self):
        cli = WhisperCLI(headless=True, debug=False)
        device = SimpleNamespace(index=5, name="Mic")
        self.audio_service.list_input_devices.return_value = [device]
        self.audio_service.select_default_device.return_value = 99

        cli._select_microphone()
        self.audio_service.select_default_device.assert_called_once()
        self.assertEqual(self.audio_service.input_device_index, 99)

    def test_select_microphone_interactive_allows_choice(self):
        cli = WhisperCLI(headless=False, debug=False)
        devices = [SimpleNamespace(index=1, name="Mic A"), SimpleNamespace(index=2, name="Mic B")]
        self.audio_service.list_input_devices.return_value = devices
        self.audio_service.select_default_device.return_value = 1

        with patch('builtins.input', side_effect=['1']):
            cli._select_microphone()

        self.assertEqual(self.audio_service.input_device_index, 2)

    def test_select_microphone_without_devices_exits(self):
        cli = WhisperCLI(headless=True, debug=False)
        self.audio_service.list_input_devices.return_value = []

        with self.assertRaises(SystemExit):
            cli._select_microphone()


class TestWhisperCLIEnvConfiguration(WhisperCLITestBase):
    def test_configure_audio_env_sets_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            cli = WhisperCLI(headless=True, debug=False)
            self.assertEqual(os.environ['ALSA_PCM_CARD'], 'default')
            self.assertEqual(os.environ['ALSA_PCM_DEVICE'], '0')
            self.assertEqual(os.environ['JACK_NO_AUDIO_RESERVATION'], '1')
            self.assertEqual(os.environ['PULSE_LATENCY_MSEC'], '30')

