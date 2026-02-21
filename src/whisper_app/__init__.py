"""
Whisper App - OpenAI Whisper voice recording with system tray GUI.

This package provides a GUI and CLI for recording audio and transcribing it
using OpenAI's Whisper model with GPU acceleration.
"""

__version__ = "0.1.0"
__author__ = "Rahul Rajaram"

from .cli import WhisperCLI
from .gui import WhisperGUI

__all__ = ["WhisperCLI", "WhisperGUI"]
