#!/usr/bin/env python3
"""Centralized configuration helpers for Whisper app components."""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Mapping, Optional

DEFAULT_BASE_DIR = Path.home() / ".whisper"
SYSTEM_INPUT_ROUTE = "system"
RECORDING_LIFECYCLE_COMMAND_ENV = "WHISPER_RECORDING_LIFECYCLE_COMMAND"


def valid_microphone_route(value: object) -> bool:
    """Return whether a serialized route has a supported stable shape."""
    if value == SYSTEM_INPUT_ROUTE:
        return True
    if not isinstance(value, str):
        return False
    kind, separator, identifier = value.partition(":")
    return bool(separator and identifier and kind in {"pipewire", "portaudio"})


@dataclass
class WhisperPaths:
    """Filesystem locations used across the application."""

    base_dir: Path = field(default_factory=lambda: DEFAULT_BASE_DIR)
    fifo_filename: str = "control.fifo"
    config_filename: str = "config"
    history_filename: str = "gui_history.json"
    lock_filename: str = "app.lock"

    def __post_init__(self) -> None:
        self.base_dir = self.base_dir.expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def fifo_path(self) -> Path:
        return self.base_dir / self.fifo_filename

    @property
    def config_path(self) -> Path:
        return self.base_dir / self.config_filename

    @property
    def history_path(self) -> Path:
        return self.base_dir / self.history_filename

    @property
    def lock_path(self) -> Path:
        return self.base_dir / self.lock_filename


@dataclass
class HotkeyConfig:
    """Configuration related to global hotkeys."""

    enabled: bool = False
    chord: str = "ctrl+alt+shift+r"


def recording_lifecycle_command_from_environment(
    environment: Optional[Mapping[str, str]] = None,
) -> tuple[str, ...]:
    """Decode an optional external recording-lifecycle command safely."""

    source = os.environ if environment is None else environment
    raw_command = source.get(RECORDING_LIFECYCLE_COMMAND_ENV, "").strip()
    if not raw_command:
        return ()
    try:
        return tuple(shlex.split(raw_command))
    except ValueError:
        return ()


@dataclass(frozen=True)
class RecordingLifecycleConfig:
    """Agnostic adapter configuration for recording boundary events."""

    command: tuple[str, ...] = field(default_factory=recording_lifecycle_command_from_environment)
    timeout_seconds: float = 10.0


@dataclass
class WhisperRuntimeConfig:
    """Runtime configuration shared by GUI, CLI, and daemons."""

    model_name: str = "large-v3"
    device_override: Optional[str] = None
    headless: bool = True
    debug: bool = False
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)
    recording_lifecycle: RecordingLifecycleConfig = field(default_factory=RecordingLifecycleConfig)
    paths: WhisperPaths = field(default_factory=WhisperPaths)


def load_microphone_config(paths: WhisperPaths) -> str:
    """Load a stable logical route, defaulting to the system policy.

    Older releases stored PortAudio indices. Those indices change whenever
    devices are connected or removed, so legacy values intentionally migrate
    to the system default instead of being reused.
    """

    try:
        if not paths.config_path.exists():
            return SYSTEM_INPUT_ROUTE
        data = paths.config_path.read_text().strip()
        if not data:
            return SYSTEM_INPUT_ROUTE
        import json

        config: Dict[str, object] = json.loads(data)
        route = config.get("input_route")
        if valid_microphone_route(route):
            return str(route)

        legacy_name = config.get("input_device_name")
        if isinstance(legacy_name, str) and legacy_name not in {"pulse", "default"}:
            return f"portaudio:{legacy_name}"
        return SYSTEM_INPUT_ROUTE
    except Exception:
        return SYSTEM_INPUT_ROUTE


def save_microphone_config(paths: WhisperPaths, input_route: str) -> None:
    """Persist a stable logical input route."""

    try:
        import json

        route = input_route if valid_microphone_route(input_route) else SYSTEM_INPUT_ROUTE
        payload = {"input_route": route}
        paths.config_path.write_text(json.dumps(payload, indent=2))
    except Exception:
        # Persistence failures should not crash the app; callers can log separately.
        pass


__all__ = [
    "HotkeyConfig",
    "RECORDING_LIFECYCLE_COMMAND_ENV",
    "RecordingLifecycleConfig",
    "SYSTEM_INPUT_ROUTE",
    "WhisperPaths",
    "WhisperRuntimeConfig",
    "load_microphone_config",
    "recording_lifecycle_command_from_environment",
    "save_microphone_config",
    "valid_microphone_route",
]
