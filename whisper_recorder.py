#!/usr/bin/env python3
import pyaudio
import wave
import whisper
import threading
import tempfile
import os
import signal
import sys
import time
import json
from datetime import datetime
from contextlib import redirect_stderr
import io

class WhisperRecorder:
    """
    A reusable whisper recorder that can be integrated into other CLIs.
    Supports persistent microphone selection and simple start/stop API.
    """
    
    def __init__(self, model_size="base", config_file=None):
        self.config_file = config_file or os.path.expanduser("~/.whisper_config.json")
        self.model_size = model_size
        self.model = None
        self.recording = False
        self.audio_data = []
        self.stream = None
        self.audio = None
        self.input_device_index = None
        
        # Audio settings
        self.chunk = 4096
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        
        # Suppress ALSA warnings
        self._suppress_audio_warnings()
        
        # Initialize components
        self._init_audio()
        self._load_config()
        
    def _suppress_audio_warnings(self):
        """Set environment variables to reduce ALSA warnings"""
        os.environ['ALSA_PCM_CARD'] = 'default'
        os.environ['ALSA_PCM_DEVICE'] = '0'
    
    def _init_audio(self):
        """Initialize PyAudio with proper error handling"""
        try:
            with redirect_stderr(io.StringIO()):
                self.audio = pyaudio.PyAudio()
        except Exception as e:
            raise RuntimeError(f"Error initializing audio: {e}")
    
    def _load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.input_device_index = config.get('input_device_index')
                    self.model_size = config.get('model_size', self.model_size)
        except Exception:
            pass  # Use defaults if config fails to load
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            config = {
                'input_device_index': self.input_device_index,
                'model_size': self.model_size
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass  # Fail silently if config can't be saved
    
    def _load_model(self):
        """Lazy load the Whisper model"""
        if self.model is None:
            print(f"🤖 Loading Whisper model ({self.model_size})...")
            self.model = whisper.load_model(self.model_size)
    
    def get_available_devices(self):
        """Get list of available input devices"""
        devices = []
        for i in range(self.audio.get_device_count()):
            try:
                device_info = self.audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    devices.append({
                        'index': i,
                        'name': device_info['name'],
                        'is_default': i == self.audio.get_default_input_device_info()['index']
                    })
            except:
                continue
        return devices
    
    def select_microphone(self):
        """Interactive microphone selection"""
        devices = self.get_available_devices()
        
        if not devices:
            raise RuntimeError("No input devices found!")
        
        print("\n🎤 Available input devices:")
        for idx, device in enumerate(devices):
            default_marker = " (DEFAULT)" if device['is_default'] else ""
            current_marker = " (CURRENT)" if device['index'] == self.input_device_index else ""
            print(f"  {idx}: {device['name']}{default_marker}{current_marker}")
        
        while True:
            try:
                choice = input(f"\nSelect microphone (0-{len(devices)-1}, or press ENTER for current/default): ").strip()
                
                if choice == "":
                    if self.input_device_index is None:
                        # Use default device
                        default_device = self.audio.get_default_input_device_info()
                        print(f"🎯 Using default input device: {default_device['name']}")
                    else:
                        current_device = self.audio.get_device_info_by_index(self.input_device_index)
                        print(f"🎯 Using current device: {current_device['name']}")
                    break
                
                choice_idx = int(choice)
                if 0 <= choice_idx < len(devices):
                    device = devices[choice_idx]
                    self.input_device_index = device['index']
                    print(f"🎯 Selected: {device['name']}")
                    self._save_config()
                    break
                else:
                    print(f"Please enter a number between 0 and {len(devices)-1}")
                    
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\nCancelled.")
                break
    
    def start_recording(self):
        """Start recording audio"""
        if self.recording:
            return False  # Already recording
        
        try:
            self.recording = True
            self.audio_data = []
            
            # Open audio stream with error handling
            with redirect_stderr(io.StringIO()):
                self.stream = self.audio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.chunk,
                    input_device_index=self.input_device_index,
                    start=False
                )
                self.stream.start_stream()
            
            # Start recording in a separate thread
            self.recording_thread = threading.Thread(target=self._record_audio, daemon=True)
            self.recording_thread.start()
            
            return True
            
        except Exception as e:
            self.recording = False
            if self.stream:
                try:
                    self.stream.close()
                except:
                    pass
                self.stream = None
            raise RuntimeError(f"Error starting recording: {e}")
    
    def _record_audio(self):
        """Internal method to record audio in thread"""
        while self.recording and self.stream:
            try:
                if self.stream.is_active():
                    data = self.stream.read(self.chunk, exception_on_overflow=False)
                    self.audio_data.append(data)
                else:
                    time.sleep(0.01)
            except OSError:
                self.recording = False
                break
            except Exception:
                self.recording = False
                break
    
    def stop_recording_and_transcribe(self):
        """Stop recording and return transcription"""
        if not self.recording:
            return None  # Not recording
        
        self.recording = False
        
        # Wait for recording thread to finish
        if hasattr(self, 'recording_thread') and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=2.0)
        
        # Clean up stream
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
            finally:
                self.stream = None
        
        # Transcribe audio
        return self._transcribe_audio()
    
    def _transcribe_audio(self):
        """Transcribe recorded audio"""
        if not self.audio_data:
            return None
        
        try:
            # Lazy load model
            self._load_model()
            
            # Create temporary wav file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_filename = temp_file.name
                
                # Write audio data to wav file
                wf = wave.open(temp_filename, 'wb')
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(self.audio_data))
                wf.close()
            
            # Transcribe with Whisper
            result = self.model.transcribe(temp_filename)
            text = result["text"].strip()
            
            # Clean up temporary file
            try:
                os.unlink(temp_filename)
            except:
                pass
            
            return text if text else None
            
        except Exception as e:
            return None
    
    def is_recording(self):
        """Check if currently recording"""
        return self.recording
    
    def cleanup(self):
        """Clean up resources"""
        if self.recording:
            self.stop_recording_and_transcribe()
        
        if self.audio:
            try:
                self.audio.terminate()
            except:
                pass
            finally:
                self.audio = None


# Global recorder instance for easy import
_recorder = None

def get_recorder():
    """Get or create global recorder instance"""
    global _recorder
    if _recorder is None:
        _recorder = WhisperRecorder()
    return _recorder

def start_recording():
    """Start recording (simple API)"""
    recorder = get_recorder()
    return recorder.start_recording()

def stop_recording():
    """Stop recording and return transcription (simple API)"""
    recorder = get_recorder()
    return recorder.stop_recording_and_transcribe()

def is_recording():
    """Check if recording (simple API)"""
    recorder = get_recorder()
    return recorder.is_recording()

def select_microphone():
    """Select microphone (simple API)"""
    recorder = get_recorder()
    return recorder.select_microphone()