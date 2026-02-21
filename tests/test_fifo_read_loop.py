"""Error-path coverage for FIFO read loop."""

from __future__ import annotations

from pathlib import Path

import pytest

from whisper_app.fifo_controller import FIFOCommandController


class DummyFile:
    def __init__(self, data: str = "", stop_event=None):
        self.data = data
        self._stop_event = stop_event

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        if self._stop_event:
            self._stop_event.set()
        return self.data


def test_read_loop_handles_missing_fifo(monkeypatch, tmp_path):
    controller = FIFOCommandController(fifo_path=str(tmp_path / "fifo"), debug=True)
    controller._stop_event.clear()

    calls = {"count": 0}

    def fake_open(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise FileNotFoundError
        controller._stop_event.set()
        return DummyFile("")

    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: controller._stop_event.set())

    controller._read_loop()
    assert calls["count"] >= 1


def test_read_loop_handles_oserror_and_dispatch(monkeypatch, tmp_path):
    controller = FIFOCommandController(fifo_path=str(tmp_path / "fifo"), debug=True)
    controller._stop_event.clear()
    received = []

    controller.on_command_received = lambda command: received.append(command)

    calls = {"count": 0}

    def fake_open(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("boom")
        return DummyFile("start", stop_event=controller._stop_event)

    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)

    controller._read_loop()

    assert "start" in received
