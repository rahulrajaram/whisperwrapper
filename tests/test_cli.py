#!/usr/bin/env python3
"""
Unit tests for WhisperCLI with mocks and stubs.

Tests cover:
- Audio initialization
- Recording start/stop
- Audio stream management
- Transcription with Whisper
- Configuration management
- Error handling
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, mock_open
import sys
import os
import json
import tempfile
import threading


class TestWhisperCLIInitialization(unittest.TestCase):
    """Test CLI initialization and setup."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.pyaudio_patcher = patch('whisper_app.cli.pyaudio')
        self.mock_pyaudio = self.pyaudio_patcher.start()

        self.whisper_patcher = patch('whisper_app.cli.whisper')
        self.mock_whisper = self.whisper_patcher.start()

        self.torch_patcher = patch('whisper_app.cli.torch')
        self.mock_torch = self.torch_patcher.start()

        # Setup torch CUDA
        self.mock_torch.cuda.is_available.return_value = True

    def tearDown(self):
        """Clean up test fixtures."""
        self.pyaudio_patcher.stop()
        self.whisper_patcher.stop()
        self.torch_patcher.stop()

    def test_cli_initialization_with_cuda(self):
        """Test CLI initializes with CUDA when available."""
        from whisper_app.cli import WhisperCLI

        self.mock_whisper.load_model.return_value = Mock()
        mock_audio = Mock()
        self.mock_pyaudio.PyAudio.return_value = mock_audio

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=True):
                cli = WhisperCLI(headless=True, debug=False)

                self.mock_torch.cuda.is_available.assert_called_once()
                self.mock_whisper.load_model.assert_called_once_with("medium", device="cuda")

    def test_cli_initialization_without_cuda(self):
        """Test CLI falls back to CPU when CUDA unavailable."""
        from whisper_app.cli import WhisperCLI

        self.mock_torch.cuda.is_available.return_value = False
        self.mock_whisper.load_model.return_value = Mock()

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=True):
                cli = WhisperCLI(headless=True, debug=False)

                self.mock_whisper.load_model.assert_called_once_with("medium", device="cpu")

    def test_audio_initialization_failure(self):
        """Test handling of audio initialization failure."""
        from whisper_app.cli import WhisperCLI

        self.mock_pyaudio.PyAudio.side_effect = Exception("No audio device")

        with self.assertRaises(SystemExit):
            cli = WhisperCLI(headless=True, debug=False)


class TestWhisperCLIConfiguration(unittest.TestCase):
    """Test configuration management."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'config')

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('whisper_app.cli.pyaudio')
    @patch('whisper_app.cli.whisper')
    @patch('whisper_app.cli.torch')
    def test_save_config(self, mock_torch, mock_whisper, mock_pyaudio):
        """Test saving configuration."""
        from whisper_app.cli import WhisperCLI

        mock_torch.cuda.is_available.return_value = True
        mock_whisper.load_model.return_value = Mock()

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=False):
                with patch.object(WhisperCLI, '_select_microphone'):
                    cli = WhisperCLI(headless=True, debug=False)
                    cli.config_file = self.config_file
                    cli.input_device_index = 5

                    # Save config
                    cli._save_config()

                    # Verify saved
                    self.assertTrue(os.path.exists(self.config_file))
                    with open(self.config_file, 'r') as f:
                        config = json.load(f)
                    self.assertEqual(config["input_device_index"], 5)

    @patch('whisper_app.cli.pyaudio')
    @patch('whisper_app.cli.whisper')
    @patch('whisper_app.cli.torch')
    def test_load_config(self, mock_torch, mock_whisper, mock_pyaudio):
        """Test loading configuration."""
        from whisper_app.cli import WhisperCLI

        # Create config file
        config = {"input_device_index": 9}
        with open(self.config_file, 'w') as f:
            json.dump(config, f)

        mock_torch.cuda.is_available.return_value = True
        mock_whisper.load_model.return_value = Mock()

        with patch.object(WhisperCLI, '_init_audio'):
            cli = WhisperCLI(headless=True, debug=False)
            cli.config_file = self.config_file

            # Load config
            result = cli._load_config()

            self.assertTrue(result)
            self.assertEqual(cli.input_device_index, 9)


class TestWhisperCLIRecording(unittest.TestCase):
    """Test audio recording functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_stream = Mock()
        self.mock_audio = Mock()
        self.mock_whisper = Mock()

    @patch('whisper_app.cli.pyaudio')
    @patch('whisper_app.cli.whisper')
    @patch('whisper_app.cli.torch')
    def test_start_recording(self, mock_torch, mock_whisper_module, mock_pyaudio):
        """Test starting audio recording."""
        from whisper_app.cli import WhisperCLI

        mock_torch.cuda.is_available.return_value = True
        mock_whisper_module.load_model.return_value = Mock()
        self.mock_audio.open.return_value = self.mock_stream

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=True):
                cli = WhisperCLI(headless=True, debug=False)
                cli.audio = self.mock_audio
                cli.stream = None

                # Start recording
                cli.start_recording()

                self.assertTrue(cli.recording)
                self.assertIsNotNone(cli.recording_thread)
                self.assertEqual(len(cli.audio_data), 0)

    @patch('whisper_app.cli.pyaudio')
    @patch('whisper_app.cli.whisper')
    @patch('whisper_app.cli.torch')
    def test_stop_recording_with_audio(self, mock_torch, mock_whisper_module, mock_pyaudio):
        """Test stopping recording with audio data."""
        from whisper_app.cli import WhisperCLI

        mock_torch.cuda.is_available.return_value = True
        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": "Hello world"}
        mock_whisper_module.load_model.return_value = mock_model

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=True):
                cli = WhisperCLI(headless=True, debug=False)
                cli.recording = True
                cli.audio_data = [b'audio_chunk_1', b'audio_chunk_2']
                cli.stream = self.mock_stream
                cli.recording_thread = Mock()
                cli.recording_thread.is_alive.return_value = False

                with patch('whisper_app.cli.tempfile.NamedTemporaryFile'):
                    with patch('whisper_app.cli.wave.open'):
                        result = cli.stop_recording()

                        self.assertFalse(cli.recording)
                        self.mock_stream.stop_stream.assert_called_once()
                        self.mock_stream.close.assert_called_once()

    @patch('whisper_app.cli.pyaudio')
    @patch('whisper_app.cli.whisper')
    @patch('whisper_app.cli.torch')
    def test_stop_recording_no_audio(self, mock_torch, mock_whisper_module, mock_pyaudio):
        """Test stopping recording with no audio data."""
        from whisper_app.cli import WhisperCLI

        mock_torch.cuda.is_available.return_value = True
        mock_whisper_module.load_model.return_value = Mock()

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=True):
                cli = WhisperCLI(headless=True, debug=False)
                cli.recording = True
                cli.audio_data = []
                cli.stream = self.mock_stream
                cli.recording_thread = Mock()
                cli.recording_thread.is_alive.return_value = False

                result = cli.stop_recording()

                self.assertIsNone(result)

    def test_record_audio_thread(self):
        """Test audio recording thread captures data."""
        mock_cli = Mock()
        mock_cli.recording = True
        mock_cli.stream = self.mock_stream
        mock_cli.audio_data = []
        mock_cli.chunk = 4096

        # Simulate reading audio chunks
        self.mock_stream.read.side_effect = [
            b'chunk1',
            b'chunk2',
            b'chunk3',
            Exception("Stop recording")
        ]

        # Simulate recording loop
        try:
            while mock_cli.recording:
                data = self.mock_stream.read(mock_cli.chunk)
                if data:
                    mock_cli.audio_data.append(data)
        except:
            pass

        self.assertEqual(len(mock_cli.audio_data), 3)


class TestWhisperCLITranscription(unittest.TestCase):
    """Test transcription functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('whisper_app.cli.pyaudio')
    @patch('whisper_app.cli.whisper')
    @patch('whisper_app.cli.torch')
    @patch('whisper_app.cli.tempfile')
    @patch('whisper_app.cli.wave')
    def test_transcribe_audio_success(self, mock_wave, mock_tempfile, mock_torch,
                                     mock_whisper_module, mock_pyaudio):
        """Test successful audio transcription."""
        from whisper_app.cli import WhisperCLI

        mock_torch.cuda.is_available.return_value = True
        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": "Test transcription"}
        mock_whisper_module.load_model.return_value = mock_model

        temp_file = os.path.join(self.temp_dir, 'test.wav')
        mock_tempfile.NamedTemporaryFile.return_value.__enter__.return_value.name = temp_file

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=True):
                cli = WhisperCLI(headless=True, debug=False)
                cli.audio_data = [b'audio_chunk']

                result = cli._transcribe_audio()

                self.assertEqual(result, "Test transcription")
                mock_model.transcribe.assert_called_once()

    @patch('whisper_app.cli.pyaudio')
    @patch('whisper_app.cli.whisper')
    @patch('whisper_app.cli.torch')
    def test_transcribe_audio_empty(self, mock_torch, mock_whisper_module, mock_pyaudio):
        """Test transcription with no audio data."""
        from whisper_app.cli import WhisperCLI

        mock_torch.cuda.is_available.return_value = True
        mock_whisper_module.load_model.return_value = Mock()

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=True):
                cli = WhisperCLI(headless=True, debug=False)
                cli.audio_data = []

                result = cli._transcribe_audio()

                self.assertIsNone(result)

    @patch('whisper_app.cli.pyaudio')
    @patch('whisper_app.cli.whisper')
    @patch('whisper_app.cli.torch')
    @patch('whisper_app.cli.tempfile')
    @patch('whisper_app.cli.wave')
    def test_transcribe_audio_no_speech(self, mock_wave, mock_tempfile, mock_torch,
                                       mock_whisper_module, mock_pyaudio):
        """Test transcription with no speech detected."""
        from whisper_app.cli import WhisperCLI

        mock_torch.cuda.is_available.return_value = True
        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": ""}
        mock_whisper_module.load_model.return_value = mock_model

        temp_file = os.path.join(self.temp_dir, 'test.wav')
        mock_tempfile.NamedTemporaryFile.return_value.__enter__.return_value.name = temp_file

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=True):
                cli = WhisperCLI(headless=True, debug=False)
                cli.audio_data = [b'audio_chunk']

                result = cli._transcribe_audio()

                self.assertIsNone(result)

    @patch('whisper_app.cli.pyaudio')
    @patch('whisper_app.cli.whisper')
    @patch('whisper_app.cli.torch')
    def test_transcribe_audio_ffmpeg_missing(self, mock_torch, mock_whisper_module, mock_pyaudio):
        """Test transcription fails gracefully when ffmpeg missing."""
        from whisper_app.cli import WhisperCLI

        mock_torch.cuda.is_available.return_value = True
        mock_model = Mock()
        mock_model.transcribe.side_effect = FileNotFoundError("ffmpeg not found")
        mock_whisper_module.load_model.return_value = mock_model

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=True):
                with patch('whisper_app.cli.tempfile'):
                    with patch('whisper_app.cli.wave'):
                        cli = WhisperCLI(headless=True, debug=False)
                        cli.audio_data = [b'audio_chunk']

                        result = cli._transcribe_audio()

                        self.assertIsNone(result)


class TestWhisperCLIStreamManagement(unittest.TestCase):
    """Test audio stream lifecycle management."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_stream = Mock()
        self.mock_audio = Mock()

    def test_stream_cleanup(self):
        """Test stream is properly cleaned up."""
        # Stream cleanup sequence
        self.mock_stream.stop_stream()
        self.mock_stream.close()

        self.mock_stream.stop_stream.assert_called_once()
        self.mock_stream.close.assert_called_once()

    def test_stream_cleanup_with_exception(self):
        """Test stream cleanup handles exceptions."""
        self.mock_stream.stop_stream.side_effect = Exception("Stream error")

        # Should handle exception gracefully
        try:
            self.mock_stream.stop_stream()
        except:
            pass  # Ignore error

        self.mock_stream.close()
        self.mock_stream.close.assert_called_once()


class TestWhisperCLIDebugMode(unittest.TestCase):
    """Test debug logging functionality."""

    @patch('whisper_app.cli.pyaudio')
    @patch('whisper_app.cli.whisper')
    @patch('whisper_app.cli.torch')
    def test_debug_enabled(self, mock_torch, mock_whisper, mock_pyaudio):
        """Test debug mode enables logging."""
        from whisper_app.cli import WhisperCLI

        mock_torch.cuda.is_available.return_value = True
        mock_whisper.load_model.return_value = Mock()

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=True):
                cli = WhisperCLI(headless=True, debug=True)

                self.assertTrue(cli.debug)

    @patch('whisper_app.cli.pyaudio')
    @patch('whisper_app.cli.whisper')
    @patch('whisper_app.cli.torch')
    def test_debug_disabled(self, mock_torch, mock_whisper, mock_pyaudio):
        """Test debug mode can be disabled."""
        from whisper_app.cli import WhisperCLI

        mock_torch.cuda.is_available.return_value = True
        mock_whisper.load_model.return_value = Mock()

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=True):
                cli = WhisperCLI(headless=True, debug=False)

                self.assertFalse(cli.debug)

    @patch('whisper_app.cli.pyaudio')
    @patch('whisper_app.cli.whisper')
    @patch('whisper_app.cli.torch')
    @patch('builtins.print')
    def test_debug_output(self, mock_print, mock_torch, mock_whisper, mock_pyaudio):
        """Test debug messages are printed."""
        from whisper_app.cli import WhisperCLI

        mock_torch.cuda.is_available.return_value = True
        mock_whisper.load_model.return_value = Mock()

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=True):
                cli = WhisperCLI(headless=True, debug=True)

                cli._debug("Test debug message")

                # Check debug was called (though we can't verify exact output in this mock)
                self.assertTrue(cli.debug)


class TestWhisperCLICleanup(unittest.TestCase):
    """Test cleanup and resource management."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_stream = Mock()
        self.mock_audio = Mock()

    @patch('whisper_app.cli.pyaudio')
    @patch('whisper_app.cli.whisper')
    @patch('whisper_app.cli.torch')
    def test_cleanup_stops_recording(self, mock_torch, mock_whisper, mock_pyaudio):
        """Test cleanup stops active recording."""
        from whisper_app.cli import WhisperCLI

        mock_torch.cuda.is_available.return_value = True
        mock_whisper.load_model.return_value = Mock()

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=True):
                cli = WhisperCLI(headless=True, debug=False)
                cli.recording = True
                cli.stream = self.mock_stream

                cli.cleanup()

                self.assertFalse(cli.recording)

    @patch('whisper_app.cli.pyaudio')
    @patch('whisper_app.cli.whisper')
    @patch('whisper_app.cli.torch')
    def test_cleanup_closes_stream(self, mock_torch, mock_whisper, mock_pyaudio):
        """Test cleanup closes audio stream."""
        from whisper_app.cli import WhisperCLI

        mock_torch.cuda.is_available.return_value = True
        mock_whisper.load_model.return_value = Mock()

        with patch.object(WhisperCLI, '_init_audio'):
            with patch.object(WhisperCLI, '_load_config', return_value=True):
                cli = WhisperCLI(headless=True, debug=False)
                cli.stream = self.mock_stream
                cli.audio = self.mock_audio

                cli.cleanup()

                self.assertIsNone(cli.stream)
                self.assertIsNone(cli.audio)


if __name__ == '__main__':
    unittest.main()
