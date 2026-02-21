"""Tests for the GUI-integrated hotkey backend."""

from __future__ import annotations

import pytest

from whisper_app.hotkeys import backend as backend_module


class ImmediateThread:
    def __init__(self, target, daemon, name=None):
        self.target = target
        self.daemon = daemon
        self.name = name
        self._alive = False

    def start(self):
        self._alive = True
        self.target()
        self._alive = False

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        self._alive = False


class StubKeyboard:
    class Key:
        ctrl = object()
        ctrl_l = ctrl
        ctrl_r = ctrl
        alt = object()
        alt_l = alt
        alt_r = alt
        shift = object()
        shift_l = shift
        shift_r = shift
        cmd = object()
        cmd_l = cmd
        cmd_r = cmd
        alt_gr = alt

    class KeyCode:
        def __init__(self, char):
            self.char = char

    class Listener:
        def __init__(self, on_press, on_release):
            self.on_press = on_press
            self.on_release = on_release
            self._alive = True

        def start(self):
            self.on_press(StubKeyboard.Key.ctrl)
            self.on_press(StubKeyboard.Key.alt)
            self.on_press(StubKeyboard.Key.shift)
            self.on_press(StubKeyboard.KeyCode("r"))
            self._alive = False

        def join(self, timeout=None):
            self._alive = False

        def stop(self):
            self._alive = False

        def is_alive(self):
            return self._alive


@pytest.fixture(autouse=True)
def stub_keyboard(monkeypatch):
    """Ensure tests never require the real pynput backend."""

    monkeypatch.setattr(backend_module, "keyboard", StubKeyboard)


def test_hotkey_backend_triggers_callback(monkeypatch):
    monkeypatch.setattr(
        backend_module.threading,
        "Thread",
        lambda target, daemon, name=None: ImmediateThread(target, daemon, name),
    )

    triggered = []

    backend = backend_module.HotkeyBackend(
        chord="ctrl+alt+shift+r",
        callback=lambda: triggered.append("hit"),
    )
    backend.start()

    assert triggered == ["hit"]
    backend.stop()


def test_hotkey_backend_stop_is_idempotent(monkeypatch):
    backend = backend_module.HotkeyBackend(chord="ctrl+r", callback=lambda: None)
    backend.stop()

    monkeypatch.setattr(
        backend_module.threading,
        "Thread",
        lambda target, daemon, name=None: ImmediateThread(target, daemon, name),
    )
    backend.start()
    backend.stop()
    backend.stop()
