"""Tests for GUI storage and locking helpers."""

from __future__ import annotations

from pathlib import Path

from whisper_app.config import WhisperPaths
from whisper_app.gui.config import GUIStorageManager


def test_gui_storage_history_roundtrip(tmp_path):
    paths = WhisperPaths(base_dir=tmp_path)
    storage = GUIStorageManager(paths)

    history = [{"timestamp": "t1", "text": "hello"}]
    storage.save_history(history)

    loaded = storage.load_history()
    assert loaded == history


def test_gui_storage_lock(tmp_path):
    paths = WhisperPaths(base_dir=tmp_path)
    storage = GUIStorageManager(paths)

    lock = storage.acquire_lock()
    try:
        lock.write_pid(123)
        assert paths.lock_path.exists()
        assert paths.lock_path.read_text().strip() == "123"
    finally:
        lock.release()
    assert not paths.lock_path.exists()


def test_gui_storage_handles_invalid_history(tmp_path):
    paths = WhisperPaths(base_dir=tmp_path)
    storage = GUIStorageManager(paths)
    storage.history_path.write_text("{bad json")
    assert storage.load_history() == []
