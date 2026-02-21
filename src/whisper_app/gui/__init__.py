"""GUI package exposing main window and helpers."""

from .main_window import WhisperGUI, main
from .presenter import WhisperPresenter

__all__ = ["WhisperGUI", "WhisperPresenter", "main"]
