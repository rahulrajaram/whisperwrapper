"""Tests for the CodexWorker helper."""

from __future__ import annotations

from typing import List, Tuple

import pytest

from whisper_app.gui.workers.codex import CodexWorker


class DummyProcess:
    def __init__(self, stdout: str, stderr: str = "", returncode: int = 0):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self.killed = False

    def communicate(self, input=None, timeout=None):
        return self._stdout, self._stderr

    def kill(self):
        self.killed = True


def test_codex_worker_success(monkeypatch, qt_app):
    calls: List[Tuple[str, int]] = []

    def fake_popen(*args, **kwargs):
        return DummyProcess("**Keyword** processed text")

    monkeypatch.setattr("subprocess.Popen", fake_popen)

    worker = CodexWorker("hello", row_index=2)
    worker.result.connect(lambda text, row: calls.append((text, row)))
    worker.run()

    assert calls == [("**Keyword** processed text", 2)]


def test_codex_worker_cli_missing(monkeypatch, qt_app):
    errors: List[str] = []

    def fake_popen(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("subprocess.Popen", fake_popen)

    worker = CodexWorker("hello")
    worker.error.connect(errors.append)
    worker.run()

    assert "Claude CLI not found" in errors[0]
