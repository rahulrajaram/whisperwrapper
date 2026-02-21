"""Helpers for GUI-specific storage and singleton locking."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import IO, List, Sequence

from ..config import WhisperPaths


class SingletonLockError(RuntimeError):
    """Raised when another GUI instance already holds the lock."""


@dataclass
class SingletonLock:
    """File-based lock using fcntl to ensure single GUI instance."""

    path: Path
    _file: IO[str] | None = None

    def acquire(self) -> None:
        import fcntl  # Imported lazily to keep Windows import errors localized.

        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            file = open(self.path, "w+")
            fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError as exc:  # pragma: no cover - exercised via integration tests
            raise SingletonLockError("Whisper GUI is already running") from exc
        self._file = file

    def write_pid(self, pid: int) -> None:
        if not self._file:
            return
        self._file.seek(0)
        self._file.truncate()
        self._file.write(str(pid))
        self._file.flush()

    def release(self) -> None:
        import fcntl

        if not self._file:
            return
        try:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        finally:
            self._file.close()
            self._file = None
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False


class GUIStorageManager:
    """Persists GUI state such as history and singleton locks."""

    def __init__(self, paths: WhisperPaths):
        self.paths = paths
        self.paths.base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def history_path(self) -> Path:
        return self.paths.history_path

    @property
    def lock_path(self) -> Path:
        return self.paths.lock_path

    def load_history(self) -> List[dict]:
        try:
            if self.history_path.exists():
                return json.loads(self.history_path.read_text())
        except Exception:
            pass
        return []

    def save_history(self, history: Sequence[dict]) -> None:
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            self.history_path.write_text(json.dumps(list(history), indent=2))
        except Exception:
            pass

    def acquire_lock(self) -> SingletonLock:
        lock = SingletonLock(self.lock_path)
        lock.acquire()
        return lock


__all__ = ["GUIStorageManager", "SingletonLock", "SingletonLockError"]
