"""Audio input device discovery and PyAudio lifecycle management."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stderr
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pyaudio

from ..config import (
    SYSTEM_INPUT_ROUTE,
    WhisperPaths,
    load_microphone_config,
    save_microphone_config,
    valid_microphone_route,
)

PACTL = "/usr/bin/pactl"
PIPEWIRE_ROUTE_PREFIX = "pipewire:"
PORTAUDIO_ROUTE_PREFIX = "portaudio:"


@dataclass(frozen=True)
class AudioDeviceInfo:
    index: int
    name: str
    max_input_channels: int


@dataclass(frozen=True)
class AudioInputChoice:
    key: str
    label: str
    source_name: Optional[str] = None
    device_name: Optional[str] = None


SYSTEM_INPUT_CHOICE = AudioInputChoice(
    key=SYSTEM_INPUT_ROUTE,
    label="System default (automatic)",
)


def parse_pipewire_sources(payload: str) -> Tuple[AudioInputChoice, ...]:
    """Reduce pactl JSON to stable, human-visible physical input choices."""
    decoded = json.loads(payload)
    if not isinstance(decoded, list):
        raise ValueError("pactl source response is not a list")

    def parse_source(item: object) -> Optional[AudioInputChoice]:
        if not isinstance(item, dict):
            return None
        properties_value = item.get("properties", {})
        properties = properties_value if isinstance(properties_value, dict) else {}
        if properties.get("media.class") != "Audio/Source":
            return None
        source_name = str(item.get("name", "")).strip()
        if not source_name:
            return None
        label = str(item.get("description") or properties.get("node.nick") or source_name)
        return AudioInputChoice(
            key=f"{PIPEWIRE_ROUTE_PREFIX}{source_name}",
            label=label,
            source_name=source_name,
        )

    choices = tuple(
        choice for choice in (parse_source(item) for item in decoded) if choice is not None
    )
    return tuple(sorted(choices, key=lambda choice: choice.label.casefold()))


class AudioInputService:
    """Owns PyAudio instance and microphone persistence."""

    _RETRYABLE_PORTAUDIO_ERRORS = frozenset((-9996, -9985))

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
        self._input_route = load_microphone_config(paths)

    @property
    def audio(self) -> pyaudio.PyAudio:
        return self._audio

    @property
    def input_device_index(self) -> Optional[int]:
        if not self._input_route.startswith(PORTAUDIO_ROUTE_PREFIX):
            return None
        return self._find_portaudio_device_index(self._input_route[len(PORTAUDIO_ROUTE_PREFIX) :])

    @input_device_index.setter
    def input_device_index(self, value: Optional[int]) -> None:
        selected_name = (
            ""
            if value is None
            else next(
                (device.name for device in self.list_input_devices() if device.index == value),
                None,
            )
        )
        self.input_route = (
            f"{PORTAUDIO_ROUTE_PREFIX}{selected_name}" if selected_name else SYSTEM_INPUT_ROUTE
        )

    @property
    def input_route(self) -> str:
        return self._input_route

    @input_route.setter
    def input_route(self, value: str) -> None:
        self._input_route = value if valid_microphone_route(value) else SYSTEM_INPUT_ROUTE
        save_microphone_config(self._paths, self._input_route)

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

    def _discover_pipewire_sources(self) -> Optional[Tuple[AudioInputChoice, ...]]:
        try:
            result = subprocess.run(
                (PACTL, "--format=json", "list", "sources"),
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
            if result.returncode != 0:
                return None
            return parse_pipewire_sources(result.stdout)
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
            return None

    def list_input_choices(self) -> Tuple[AudioInputChoice, ...]:
        """List the logical default and the cleanest available device inventory.

        A working PipeWire inventory is authoritative. PortAudio's direct ALSA
        devices are exposed only as a degraded fallback; mixing both views
        produces duplicate hardware plus implementation details such as
        ``sysdefault`` and ``lavrate`` in the desktop settings dialog.
        """
        discovered = self._discover_pipewire_sources()
        if discovered is not None:
            return (SYSTEM_INPUT_CHOICE, *discovered)

        direct_choices = tuple(
            AudioInputChoice(
                key=f"{PORTAUDIO_ROUTE_PREFIX}{device.name}",
                label=f"{device.name} (direct)",
                device_name=device.name,
            )
            for device in self.list_input_devices()
            if "(hw:" in device.name.casefold()
        )
        return (SYSTEM_INPUT_CHOICE, *direct_choices)

    def _find_portaudio_device_index(self, name: str) -> Optional[int]:
        return next(
            (device.index for device in self.list_input_devices() if device.name == name),
            None,
        )

    def safe_input_device_index(self) -> Optional[int]:
        """Resolve a stable preference, falling back to the system default.

        PipeWire sources use the logical Pulse device plus ``PULSE_SOURCE``;
        direct PortAudio choices are re-resolved by name on every recording.
        Missing explicit choices temporarily fall back to the system route.
        """
        if self._input_route == SYSTEM_INPUT_ROUTE:
            os.environ.pop("PULSE_SOURCE", None)
            return None

        if self._input_route.startswith(PIPEWIRE_ROUTE_PREFIX):
            source_name = self._input_route[len(PIPEWIRE_ROUTE_PREFIX) :]
            discovered = self._discover_pipewire_sources()
            available = discovered is None or any(
                choice.source_name == source_name for choice in discovered
            )
            pulse_index = self._find_portaudio_device_index("pulse")
            if available and pulse_index is not None:
                os.environ["PULSE_SOURCE"] = source_name
                return pulse_index
            os.environ.pop("PULSE_SOURCE", None)
            return None

        os.environ.pop("PULSE_SOURCE", None)
        device_name = self._input_route[len(PORTAUDIO_ROUTE_PREFIX) :]
        return self._find_portaudio_device_index(device_name)

    def open_input_stream(self, **kwargs):
        """Open against the current system route, retrying once after churn."""
        try:
            return self._audio.open(
                **kwargs,
                input_device_index=self.safe_input_device_index(),
            )
        except OSError as exc:
            code = exc.args[0] if exc.args else None
            if code not in self._RETRYABLE_PORTAUDIO_ERRORS:
                raise

        self.terminate()
        self._audio = self._init_audio()
        return self._audio.open(
            **kwargs,
            input_device_index=self.safe_input_device_index(),
        )

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


__all__ = [
    "AudioDeviceInfo",
    "AudioInputChoice",
    "AudioInputService",
    "SYSTEM_INPUT_CHOICE",
    "parse_pipewire_sources",
]
