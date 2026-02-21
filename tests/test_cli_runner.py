"""Tests for the Whisper CLI facade."""

from __future__ import annotations

import os
import signal
import sys
from types import SimpleNamespace

import pytest

from whisper_app import cli as cli_module
from whisper_app.cli import WhisperCLI


class StubAudioService:
    def __init__(self):
        self.input_device_index = None
        self.devices = [
            SimpleNamespace(index=0, name="Mic A"),
            SimpleNamespace(index=1, name="Mic B"),
        ]

    def list_input_devices(self):
        return self.devices

    def select_default_device(self):
        return 1


class StubRecordingController:
    def __init__(self, *_, **__):
        self.audio_service = StubAudioService()
        self.recording = False

    def start(self):
        self.recording = True

    def stop(self):
        self.recording = False
        return "transcript"

    def cleanup(self):
        self.cleaned = True


class StubCallbacks:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.fixture(autouse=True)
def patch_cli_dependencies(monkeypatch):
    monkeypatch.setattr(cli_module, "WhisperRuntimeConfig", lambda **kwargs: SimpleNamespace(paths=SimpleNamespace(), hotkeys=SimpleNamespace()))
    monkeypatch.setattr(cli_module, "WhisperRecordingController", lambda *args, **kwargs: StubRecordingController())
    monkeypatch.setattr(cli_module, "RecordingEventCallbacks", StubCallbacks)


def test_cli_headless_run(monkeypatch, tmp_path):
    fifo = tmp_path / "fifo"
    os.environ["WHISPER_TRANSCRIPT_FIFO"] = str(fifo)

    # Simulate immediate ENTER
    monkeypatch.setattr("builtins.input", lambda *args, **kwargs: "")
    monkeypatch.setattr(WhisperCLI, "_start_spinner", lambda self: None)
    monkeypatch.setattr(WhisperCLI, "_stop_spinner", lambda self: None)

    cli = WhisperCLI(headless=True, force_configure=True)
    result = cli.run_headless()

    assert result == "transcript"
    assert fifo.read_text() == "transcript"


def test_cli_write_to_fifo_no_path(monkeypatch):
    cli = WhisperCLI(headless=True, force_configure=True)
    os.environ.pop("WHISPER_TRANSCRIPT_FIFO", None)
    cli._write_to_fifo("ignored")  # Should not raise


def test_cli_select_microphone_interactive(monkeypatch):
    controller = StubRecordingController()
    monkeypatch.setattr(cli_module, "WhisperRecordingController", lambda *args, **kwargs: controller)

    inputs = iter(["", "0"])
    monkeypatch.setattr("builtins.input", lambda *args: next(inputs))

    cli = WhisperCLI(headless=False, force_configure=True)
    assert controller.audio_service.input_device_index == 1


def test_cli_select_microphone_invalid_input(monkeypatch):
    controller = StubRecordingController()
    monkeypatch.setattr(cli_module, "WhisperRecordingController", lambda *args, **kwargs: controller)

    inputs = iter(["abc", "-1", "1"])
    monkeypatch.setattr("builtins.input", lambda *args: next(inputs))

    cli = WhisperCLI(headless=False, force_configure=True)
    assert controller.audio_service.input_device_index == 1


def test_cli_run_loop(monkeypatch):
    controller = StubRecordingController()
    controller.audio_service.input_device_index = 0
    monkeypatch.setattr(cli_module, "WhisperRecordingController", lambda *args, **kwargs: controller)

    inputs = iter(["", "", "quit"])
    monkeypatch.setattr("builtins.input", lambda *args: next(inputs))

    cli = WhisperCLI(headless=False, force_configure=False)
    cli.run()
    assert not cli.recording


def test_cli_spinner_controls(monkeypatch):
    cli = WhisperCLI(headless=True, force_configure=True)

    class DummyThread:
        def __init__(self, target, daemon):
            self.target = target
            self.daemon = daemon
            self._alive = False

        def start(self):
            self._alive = True

        def is_alive(self):
            return self._alive

        def join(self, timeout=None):
            self._alive = False

    monkeypatch.setattr("threading.Thread", lambda target, daemon: DummyThread(target, daemon))
    cli._start_spinner()
    cli._stop_spinner()


def test_cli_signal_handler(monkeypatch, tmp_path):
    os.environ["WHISPER_TRANSCRIPT_FIFO"] = str(tmp_path / "fifo")
    cli = WhisperCLI(headless=True, force_configure=True)
    cli.controller.recording = True

    exits = []
    monkeypatch.setattr("sys.exit", lambda code=0: exits.append(code))

    cli.signal_handler(signal.SIGTERM, None)
    assert exits == [0]


def test_cli_main_variants(monkeypatch):
    calls = []

    class DummyCLI:
        def __init__(self, headless=False, force_configure=False, debug=False):
            calls.append((headless, force_configure, debug))

        def run_headless(self):
            calls.append("headless")

        def run(self):
            calls.append("run")

    monkeypatch.setattr(cli_module, "WhisperCLI", DummyCLI)

    monkeypatch.setattr(sys, "argv", ["whisper", "--headless"])
    cli_module.main()

    monkeypatch.setattr(sys, "argv", ["whisper", "--configure"])
    cli_module.main()

    monkeypatch.setattr(sys, "argv", ["whisper"])
    cli_module.main()

    assert calls == [
        (True, False, False),
        "headless",
        (False, True, False),
        (False, False, False),
        "run",
    ]
