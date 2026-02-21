#!/usr/bin/env python3
"""Centralized configuration helpers for Whisper app components."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


DEFAULT_BASE_DIR = Path.home() / ".whisper"


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


@dataclass
class WhisperRuntimeConfig:
    """Runtime configuration shared by GUI, CLI, and daemons."""

    model_name: str = "large-v3"
    device_override: Optional[str] = None
    headless: bool = True
    debug: bool = False
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)
    paths: WhisperPaths = field(default_factory=WhisperPaths)


def load_microphone_config(paths: WhisperPaths) -> Optional[int]:
    """Load persisted microphone selection if available."""

    try:
        if not paths.config_path.exists():
            return None
        data = paths.config_path.read_text().strip()
        if not data:
            return None
        import json

        config: Dict[str, object] = json.loads(data)
        index = config.get("input_device_index")
        return int(index) if isinstance(index, int) else None
    except Exception:
        return None


def save_microphone_config(paths: WhisperPaths, input_device_index: Optional[int]) -> None:
    """Persist selected microphone index for future sessions."""

    try:
        import json

        payload = {"input_device_index": input_device_index}
        paths.config_path.write_text(json.dumps(payload, indent=2))
    except Exception:
        # Persistence failures should not crash the app; callers can log separately.
        pass


__all__ = [
    "HotkeyConfig",
    "WhisperPaths",
    "WhisperRuntimeConfig",
    "load_microphone_config",
    "save_microphone_config",
]
