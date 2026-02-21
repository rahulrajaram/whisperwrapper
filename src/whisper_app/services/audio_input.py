"""Audio input device discovery and PyAudio lifecycle management."""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stderr
from dataclasses import dataclass
from typing import List, Optional

import pyaudio

from ..config import WhisperPaths, load_microphone_config, save_microphone_config


@dataclass
class AudioDeviceInfo:
    index: int
    name: str
    max_input_channels: int


class AudioInputService:
    """Owns PyAudio instance and microphone persistence."""

    def __init__(
        self,
        *,
        headless: bool,
        paths: WhisperPaths,
        debug: bool = False,
    ) -> None:
        self._headless = headless
        self._debug = debug
        self._paths = paths
        self._audio = self._init_audio()
        self._input_device_index: Optional[int] = load_microphone_config(paths)

    @property
    def audio(self) -> pyaudio.PyAudio:
        return self._audio

    @property
    def input_device_index(self) -> Optional[int]:
        return self._input_device_index

    @input_device_index.setter
    def input_device_index(self, value: Optional[int]) -> None:
        self._input_device_index = value
        save_microphone_config(self._paths, value)

    def _init_audio(self) -> pyaudio.PyAudio:
        if self._headless:
            import os

            os.environ.setdefault("JACK_NO_AUDIO_RESERVATION", "1")
            os.environ.setdefault("PULSE_LATENCY_MSEC", "30")

        stderr_buffer: io.TextIOBase = io.StringIO()
        with redirect_stderr(stderr_buffer):
            try:
                return pyaudio.PyAudio()
            finally:
                if self._debug:
                    sys.stderr.write(stderr_buffer.getvalue())

    def list_input_devices(self) -> List[AudioDeviceInfo]:
        devices: List[AudioDeviceInfo] = []
        for idx in range(self._audio.get_device_count()):
            try:
                info = self._audio.get_device_info_by_index(idx)
            except Exception:
                continue
            if info.get("maxInputChannels", 0) > 0:
                devices.append(
                    AudioDeviceInfo(
                        index=idx,
                        name=info.get("name", f"Device {idx}"),
                        max_input_channels=int(info.get("maxInputChannels", 0)),
                    )
                )
        return devices

    def select_default_device(self) -> Optional[int]:
        try:
            default_device = self._audio.get_default_input_device_info()
            return int(default_device.get("index"))
        except Exception:
            return None

    def terminate(self) -> None:
        try:
            self._audio.terminate()
        except Exception:
            pass


__all__ = ["AudioInputService", "AudioDeviceInfo"]
