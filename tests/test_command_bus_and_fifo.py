"""Tests for FIFO controller and command bus layers."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Callable, List
from unittest.mock import MagicMock

import pytest

from whisper_app.command_bus import CommandBus
from whisper_app.fifo_controller import FIFOCommandController
from whisper_app.ipc_controller import CommandController


class FakeThread:
    def __init__(self, target: Callable, daemon: bool, name: str):
        self.target = target
        self.daemon = daemon
        self.name = name
        self.started = False
        self._alive = False
        self.join_called = False

    def start(self):
        self.started = True
        self._alive = True

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        self.join_called = True
        self._alive = False


def test_fifo_controller_start_creates_fifo_and_thread(monkeypatch, tmp_path):
    fifo_path = tmp_path / "control.fifo"
    threads: List[FakeThread] = []

    def fake_thread(target, daemon, name):
        thread = FakeThread(target, daemon, name)
        threads.append(thread)
        return thread

    monkeypatch.setattr("whisper_app.fifo_controller.threading.Thread", fake_thread)

    controller = FIFOCommandController(fifo_path=str(fifo_path))
    controller.start()

    assert fifo_path.exists()
    assert controller.is_running
    assert threads[0].started


def test_fifo_controller_stop_cleans_up(monkeypatch, tmp_path):
    fifo_path = tmp_path / "control.fifo"
    thread = FakeThread(lambda: None, daemon=True, name="FIFOReader")

    def fake_thread(target, daemon, name):
        thread.target = target
        return thread

    monkeypatch.setattr("whisper_app.fifo_controller.threading.Thread", fake_thread)

    controller = FIFOCommandController(fifo_path=str(fifo_path))
    controller.start()
    controller.stop()

    assert not controller.is_running
    assert not fifo_path.exists()
    assert thread.join_called


def test_fifo_read_loop_dispatches_command(monkeypatch, tmp_path):
    fifo_path = tmp_path / "control.fifo"
    fifo_path.parent.mkdir(parents=True, exist_ok=True)

    controller = FIFOCommandController(fifo_path=str(fifo_path))
    received: List[str] = []
    controller.on_command_received = lambda cmd: received.append(cmd)

    # Inject fake file contents and stop after one loop
    class FakeFile:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            controller._stop_event.set()
            return "start"

    def fake_open(path, mode="r", *args, **kwargs):
        return FakeFile()

    monkeypatch.setattr("builtins.open", fake_open)
    controller._read_loop()

    assert received == ["start"]


def test_command_bus_subscribes_and_dispatches():
    controller = MagicMock(spec=CommandController)
    bus = CommandBus(controller)
    seen: List[str] = []
    bus.subscribe("start", lambda cmd: seen.append(cmd))

    bus._dispatch("start")

    assert seen == ["start"]


def test_command_bus_start_stop(monkeypatch):
    controller = MagicMock(spec=CommandController)
    bus = CommandBus(controller)

    bus.start()
    bus.stop()

    controller.start.assert_called_once()
    controller.stop.assert_called_once()


def test_command_bus_rejects_unknown_command():
    controller = MagicMock(spec=CommandController)
    bus = CommandBus(controller)

    with pytest.raises(ValueError):
        bus.subscribe("foo", lambda _: None)
