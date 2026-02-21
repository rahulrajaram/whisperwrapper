"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest
from PyQt6.QtWidgets import QApplication

from tests.helpers import ensure_whisper_module

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ensure_whisper_module()


@pytest.fixture(scope="session")
def qt_app():
    """Provide a QApplication instance for Qt-dependent tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
