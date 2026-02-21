"""Tests for lightweight GUI helper modules."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace
from typing import List

import pytest
from PyQt6.QtWidgets import QLabel, QMainWindow, QTableWidget

from whisper_app.gui import actions as actions_module
from whisper_app.gui.actions import open_project_terminal, show_microphone_settings
from whisper_app.gui.history_view import refresh_history_table
from whisper_app.gui.ui import build_main_interface


class DummyStatusBar:
    def __init__(self):
        self.messages: List[str] = []

    def showMessage(self, message: str):
        self.messages.append(message)


@dataclass
class DummyPresenter:
    history: List[dict]
    selected_row: int | None = None

    def __post_init__(self):
        self.copy_calls: List[int] = []
        self.delete_calls: List[int] = []
        self.toggle_calls: List[int] = []
        self.selected_rows: set = set()  # For multi-select support
        self.last_selected_row: int | None = None

    def copy_to_clipboard(self, row: int):
        self.copy_calls.append(row)

    def delete_history_item(self, row: int):
        self.delete_calls.append(row)

    def toggle_protection(self, row: int):
        self.toggle_calls.append(row)

    def select_row(self, row: int, shift: bool = False, ctrl: bool = False):
        """Handle row selection with shift/ctrl modifiers."""
        if shift and self.last_selected_row is not None:
            start = min(self.last_selected_row, row)
            end = max(self.last_selected_row, row) + 1
            self.selected_rows.update(range(start, end))
        elif ctrl:
            if row in self.selected_rows:
                self.selected_rows.discard(row)
            else:
                self.selected_rows.add(row)
        else:
            self.selected_rows = {row}
        self.last_selected_row = row

    def delete_selected(self):
        """Delete all selected rows."""
        self.delete_calls.extend(sorted(self.selected_rows, reverse=True))

    def toggle_protection_selected(self):
        """Toggle protection for all selected rows."""
        self.toggle_calls.extend(sorted(self.selected_rows))

    def get_filtered_history(self, project_id=None):
        """Return history filtered by project (for testing, return all)."""
        return self.history


class DummyGUI:
    def __init__(self, presenter: DummyPresenter):
        self.presenter = presenter
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(2)
        self._status_bar = DummyStatusBar()
        self.status_label = QLabel()
        self.clicked_rows: List[tuple[int, int]] = []

    def statusBar(self):
        return self._status_bar

    def on_table_cell_clicked(self, row: int, column: int):
        self.clicked_rows.append((row, column))


def test_refresh_history_table_populates_rows(qt_app):
    presenter = DummyPresenter(
        history=[
            {"timestamp": "t1", "text": "alpha", "protected": False},
            {"timestamp": "t2", "text": "beta", "protected": True},
        ]
    )
    gui = DummyGUI(presenter)

    refresh_history_table(gui)

    assert gui.history_table.rowCount() == 2
    assert gui.history_table.columnCount() == 2
    # Verify both rows have text content in column 1
    text_widget_0 = gui.history_table.cellWidget(0, 1)
    text_widget_1 = gui.history_table.cellWidget(1, 1)
    assert text_widget_0 is not None
    assert text_widget_1 is not None


class FakeGUIForActions:
    def __init__(self):
        self.status_bar = DummyStatusBar()
        self.status_label = QLabel()
        self.recording_controller = None

    def statusBar(self):
        return self.status_bar


def test_open_project_terminal_success(monkeypatch):
    gui = FakeGUIForActions()
    calls: List[List[str]] = []

    class DummyProcess:
        pass

    def fake_popen(cmd, start_new_session):
        calls.append(cmd)
        return DummyProcess()

    monkeypatch.setattr("subprocess.Popen", fake_popen)

    open_project_terminal(gui)

    assert calls, "should try at least one terminal command"
    assert "Terminal" in gui.statusBar().messages[-1]


def test_open_project_terminal_failure(monkeypatch):
    gui = FakeGUIForActions()

    def fake_popen(cmd, start_new_session):
        raise FileNotFoundError

    monkeypatch.setattr("subprocess.Popen", fake_popen)

    open_project_terminal(gui)

    assert "❌" in gui.status_label.text()
    assert "No terminal found" in gui.statusBar().messages[-1]


class FakeDevice:
    def __init__(self, index, name):
        self.index = index
        self.name = name


class FakeAudioService:
    def __init__(self):
        self.input_device_index = 2
        self._devices = [FakeDevice(1, "Mic A"), FakeDevice(2, "Mic B")]

    def list_input_devices(self):
        return self._devices


class StubSignal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self):
        for cb in list(self.callbacks):
            cb()


class StubButton:
    instances: List["StubButton"] = []

    def __init__(self, text=""):
        self.text_value = text
        self.clicked = StubSignal()
        StubButton.instances.append(self)

    def setToolTip(self, *_):
        pass

    def setStyleSheet(self, *_):
        pass

    def click(self):
        self.clicked.emit()


class StubComboBox:
    last_instance: "StubComboBox" | None = None

    def __init__(self):
        self.items: List[tuple[str, int]] = []
        self._index = 0
        StubComboBox.last_instance = self

    def addItem(self, text, data):
        self.items.append((text, data))

    def setCurrentIndex(self, index):
        self._index = index

    def currentIndex(self):
        return self._index

    def currentText(self):
        return self.items[self._index][0] if self.items else ""

    def itemData(self, index):
        return self.items[index][1]


class StubDialog:
    last_instance: "StubDialog" | None = None

    def __init__(self, *args, **kwargs):
        self.accepted = False
        self.rejected = False
        StubDialog.last_instance = self

    def setWindowTitle(self, *_):
        pass

    def setGeometry(self, *_):
        pass

    def exec(self):
        return 0

    def accept(self):
        self.accepted = True

    def reject(self):
        self.rejected = True


class StubLayout:
    def __init__(self, *args, **kwargs):
        pass

    def addWidget(self, *_):
        pass

    def addLayout(self, *_):
        pass


class StubLabel:
    def __init__(self, *_):
        pass


def test_show_microphone_settings_updates_device(monkeypatch):
    gui = FakeGUIForActions()
    gui.recording_controller = type(
        "RC", (), {"audio_service": FakeAudioService()}
    )()
    StubButton.instances = []

    widget_module = ModuleType("PyQt6.QtWidgets")
    widget_module.QDialog = StubDialog
    widget_module.QVBoxLayout = StubLayout
    widget_module.QHBoxLayout = StubLayout
    widget_module.QLabel = StubLabel
    widget_module.QPushButton = StubButton
    widget_module.QComboBox = StubComboBox
    monkeypatch.setitem(sys.modules, "PyQt6.QtWidgets", widget_module)

    show_microphone_settings(gui)

    for btn in StubButton.instances:
        btn.click()
        if gui.recording_controller.audio_service.input_device_index == 2:
            break

    assert gui.recording_controller.audio_service.input_device_index == 2
    assert "Microphone settings saved" in gui.statusBar().messages[-1]


def test_show_microphone_settings_handles_missing_devices(monkeypatch):
    gui = FakeGUIForActions()
    audio_service = FakeAudioService()
    audio_service._devices = []
    gui.recording_controller = type(
        "RC", (), {"audio_service": audio_service}
    )()

    show_microphone_settings(gui)

    assert gui.status_label.text() == "❌ No input devices found"


class StubMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.calls: List[str] = []

    def start_recording(self):
        self.calls.append("start")

    def stop_recording(self):
        self.calls.append("stop")

    def clear_history(self):
        self.calls.append("clear")

    def on_codex_button_clicked(self):
        self.calls.append("codex")

    def on_terminal_button_clicked(self):
        self.calls.append("terminal")

    def on_settings_button_clicked(self):
        self.calls.append("settings")

    def on_table_cell_clicked(self, row: int, column: int):
        self.calls.append(f"cell:{row}:{column}")


def test_build_main_interface_wires_button_callbacks(qt_app):
    window = StubMainWindow()

    build_main_interface(window)

    assert window.history_table.columnCount() == 2

    window.start_button.click()
    window.stop_button.click()
    window.clear_button.click()
    window.codex_button.click()
    window.terminal_button.click()
    window.settings_button.click()

    assert window.calls == ["start", "stop", "clear", "codex", "terminal", "settings"]
