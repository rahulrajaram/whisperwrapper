"""Tests for shared configuration helpers."""

from __future__ import annotations

from pathlib import Path

from whisper_app.config import (
    WhisperPaths,
    load_microphone_config,
    save_microphone_config,
)


def test_whisper_paths_resolves_locations(tmp_path):
    paths = WhisperPaths(base_dir=tmp_path)

    assert paths.fifo_path == tmp_path / "control.fifo"
    assert paths.config_path == tmp_path / "config"
    assert paths.history_path == tmp_path / "gui_history.json"
    assert paths.lock_path == tmp_path / "app.lock"


def test_microphone_config_roundtrip(tmp_path):
    paths = WhisperPaths(base_dir=tmp_path)
    save_microphone_config(paths, 7)
    assert load_microphone_config(paths) == 7


def test_microphone_config_handles_missing_and_invalid(tmp_path):
    paths = WhisperPaths(base_dir=tmp_path)

    # Missing file returns None
    assert load_microphone_config(paths) is None

    # Invalid payload returns None without raising
    paths.config_path.write_text("not json")
    assert load_microphone_config(paths) is None
