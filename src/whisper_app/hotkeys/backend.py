"""Reusable hotkey listener built on pynput."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable, Iterable, Set

try:
    from pynput import keyboard
except ImportError:  # pragma: no cover - optional dependency
    keyboard = None  # type: ignore


logger = logging.getLogger(__name__)

EXTRA_MODIFIER_SCANCODES = {
    # Shift variants
    65505: "shift",
    65506: "shift",
    # Control variants
    65507: "ctrl",
    65508: "ctrl",
    # Alt / Meta variants frequently seen on X11/Wayland
    65511: "alt",
    65512: "alt",
    65513: "alt",
    65514: "alt",
}

HotkeyCallback = Callable[[], None]


@dataclass
class HotkeyListenerHandle:
    listener: "keyboard.Listener"

    def stop(self) -> None:
        try:
            self.listener.stop()
        except Exception:
            pass


class HotkeyBackend:
    """Listens for a key chord and invokes a callback."""

    def __init__(
        self,
        *,
        chord: str,
        callback: HotkeyCallback,
    ) -> None:
        if keyboard is None:
            raise RuntimeError("pynput is not available")
        self.chord = chord
        self.callback = callback
        self._listener_handle: HotkeyListenerHandle | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._modifiers = self._parse_modifiers()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            logger.debug("HotkeyBackend already running for chord %s", self.chord)
            return
        logger.info("Starting HotkeyBackend for chord %s", self.chord)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_listener, daemon=True, name="HotkeyBackend")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._listener_handle:
            self._listener_handle.stop()
            self._listener_handle = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            if self._thread.is_alive():
                logger.warning("Hotkey thread did not exit within timeout for chord %s; continuing shutdown", self.chord)
        self._thread = None
        logger.info("Stopped HotkeyBackend for chord %s", self.chord)

    def _parse_modifiers(self) -> Set[str]:
        parts = self.chord.lower().split("+")
        return set(parts[:-1])  # modifiers only; last is trigger key

    def _run_listener(self) -> None:
        modifiers_pressed: Set[str] = set()
        trigger_key = self.chord.lower().split("+")[-1]

        modifier_mapping = {
            keyboard.Key.ctrl: "ctrl",
            keyboard.Key.ctrl_l: "ctrl",
            keyboard.Key.ctrl_r: "ctrl",
            keyboard.Key.alt: "alt",
            keyboard.Key.alt_l: "alt",
            keyboard.Key.alt_r: "alt",
            keyboard.Key.shift: "shift",
            keyboard.Key.shift_l: "shift",
            keyboard.Key.shift_r: "shift",
            keyboard.Key.cmd: "cmd",
            keyboard.Key.cmd_l: "cmd",
            keyboard.Key.cmd_r: "cmd",
            keyboard.Key.alt_gr: "alt",
        }

        def _modifier_from_key(key_obj):
            modifier = modifier_mapping.get(key_obj)
            if modifier:
                logger.debug("Modifier detected via mapping: %s (%s)", modifier, _describe_key(key_obj))
                return modifier
            if isinstance(key_obj, keyboard.KeyCode):
                vk = getattr(key_obj, "vk", None)
                if vk in EXTRA_MODIFIER_SCANCODES:
                    modifier = EXTRA_MODIFIER_SCANCODES[vk]
                    logger.debug("Modifier detected via vk %s: %s (%s)", vk, modifier, _describe_key(key_obj))
                    return modifier
            return None

        def _keycode_matches_trigger(key_obj):
            if not isinstance(key_obj, keyboard.KeyCode):
                return False
            char = getattr(key_obj, "char", None)
            vk = getattr(key_obj, "vk", None)
            normalized = (char or "").lower() if char else None
            if not normalized and isinstance(vk, int) and 32 <= vk <= 126:
                normalized = chr(vk).lower()
            logger.debug(
                "KeyCode details for chord detection: %s normalized=%s",
                _describe_key(key_obj),
                normalized,
            )
            return normalized == trigger_key

        def on_press(key):  # pragma: no cover - relies on pynput
            logger.debug("Hotkey on_press: %s (modifiers=%s)", _describe_key(key), sorted(modifiers_pressed))
            modifier = _modifier_from_key(key)
            if modifier:
                modifiers_pressed.add(modifier)
                return

            if _keycode_matches_trigger(key) and self._modifiers <= modifiers_pressed:
                logger.info("Hotkey chord %s detected", self.chord)
                self.callback()

        def on_release(key):  # pragma: no cover - relies on pynput
            modifier = _modifier_from_key(key)
            if modifier and modifier in modifiers_pressed:
                modifiers_pressed.remove(modifier)
            logger.debug("Hotkey on_release: %s (modifiers=%s)", _describe_key(key), sorted(modifiers_pressed))

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.daemon = True
        self._listener_handle = HotkeyListenerHandle(listener=listener)
        listener.start()

        try:
            while listener.is_alive():
                if self._stop_event.is_set():
                    break
                listener.join(timeout=0.25)
        finally:
            if listener.is_alive():
                try:
                    listener.stop()
                except Exception:
                    pass
                listener.join(timeout=0.5)
            self._listener_handle = None


__all__ = ["HotkeyBackend", "HotkeyListenerHandle"]
def _describe_key(key) -> str:
    return (
        f"repr={key!r} type={type(key).__name__} "
        f"char={getattr(key, 'char', None)!r} vk={getattr(key, 'vk', None)!r}"
    )
