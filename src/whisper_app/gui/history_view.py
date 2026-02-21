"""Helpers for rendering the history table."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QPushButton, QTableWidgetItem

if False:  # pragma: no cover - for typing only
    from .main_window import WhisperGUI

from .utils import markdown_to_html


class ClickableLabel(QLabel):
    clicked = pyqtSignal(int)

    def __init__(self, text: str, row_index: int, parent=None):
        super().__init__(text, parent)
        self.row_index = row_index

    def mousePressEvent(self, event):  # pragma: no cover - Qt event hook
        self.clicked.emit(self.row_index)
        super().mousePressEvent(event)


def refresh_history_table(gui: "WhisperGUI") -> None:
    table = gui.history_table

    # Filter history by current project
    history = gui.presenter.get_filtered_history()
    table.setRowCount(len(history))

    # Enable context menu on table
    table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    if not hasattr(gui, '_history_context_menu_connected'):
        table.customContextMenuRequested.connect(
            lambda pos: _show_recording_context_menu(gui, pos)
        )
        gui._history_context_menu_connected = True

    for row, item in enumerate(history):
        timestamp_item = QTableWidgetItem(item.get("timestamp", ""))
        timestamp_item.setFlags(timestamp_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        table.setItem(row, 0, timestamp_item)

        html_text = markdown_to_html(item.get("text", ""))
        text_label = ClickableLabel(html_text, row)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text_label.clicked.connect(lambda r=row: gui.on_table_cell_clicked(r, 1))
        table.setCellWidget(row, 1, text_label)

        copy_button = QPushButton("📋 Copy")
        copy_button.setToolTip("Copy to clipboard")
        copy_button.setStyleSheet(
            """
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 5px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """
        )
        copy_button.clicked.connect(lambda checked, r=row: gui.presenter.copy_to_clipboard(r))
        table.setCellWidget(row, 2, copy_button)

        if gui.presenter.selected_row == row:
            delete_button = QPushButton("🗑 Delete")
            delete_button.setToolTip("Delete this item (overrides protection)")
            delete_button.setStyleSheet(
                """
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    padding: 5px;
                    border-radius: 3px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """
            )
            delete_button.clicked.connect(lambda checked, r=row: gui.presenter.delete_history_item(r))
            table.setCellWidget(row, 3, delete_button)
        else:
            is_protected = item.get("protected", False)
            lock_button = QPushButton("🔒" if is_protected else "🔓")
            lock_button.setToolTip(
                "Protected - Click to unprotect" if is_protected else "Unprotected - Click to protect"
            )
            lock_button.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {'#FF9800' if is_protected else '#999999'};
                    color: white;
                    padding: 5px;
                    border-radius: 3px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {'#FFB74D' if is_protected else '#666666'};
                }}
            """
            )
            lock_button.clicked.connect(lambda checked, r=row: gui.presenter.toggle_protection(r))
            table.setCellWidget(row, 3, lock_button)

    gui.statusBar().showMessage("History updated")


def _show_recording_context_menu(gui: "WhisperGUI", position) -> None:
    """Show context menu for recording operations."""
    from PyQt6.QtWidgets import QMenu

    table = gui.history_table
    row = table.rowAt(position.y())
    if row < 0:
        return

    menu = QMenu(gui)

    # Copy action
    copy_action = menu.addAction("📋 Copy to Project")
    copy_action.triggered.connect(lambda: _copy_recording_to_project(gui, row))

    # Move action
    move_action = menu.addAction("➡️ Move to Project")
    move_action.triggered.connect(lambda: _move_recording_to_project(gui, row))

    # Delete action
    delete_action = menu.addAction("🗑️ Delete")
    delete_action.triggered.connect(lambda: gui.presenter.delete_history_item(row))

    # Process with Claude action
    process_action = menu.addAction("🤖 Process with Claude")
    process_action.triggered.connect(lambda: _process_with_claude(gui, row))

    menu.exec(table.viewport().mapToGlobal(position))


def _copy_recording_to_project(gui: "WhisperGUI", row: int) -> None:
    """Copy recording to another project."""
    from PyQt6.QtWidgets import QInputDialog

    projects = gui.presenter.project_manager.projects
    project_names = [p.name for p in projects]

    if not project_names:
        return

    project_name, ok = QInputDialog.getItem(
        gui,
        "Copy to Project",
        "Select target project:",
        project_names,
        0,
        False
    )

    if ok and project_name:
        target_project = next((p for p in projects if p.name == project_name), None)
        if target_project:
            gui.presenter.copy_recording_to_project(row, target_project.id)


def _move_recording_to_project(gui: "WhisperGUI", row: int) -> None:
    """Move recording to another project."""
    from PyQt6.QtWidgets import QInputDialog

    projects = gui.presenter.project_manager.projects
    project_names = [p.name for p in projects]

    if not project_names:
        return

    project_name, ok = QInputDialog.getItem(
        gui,
        "Move to Project",
        "Select target project:",
        project_names,
        0,
        False
    )

    if ok and project_name:
        target_project = next((p for p in projects if p.name == project_name), None)
        if target_project:
            gui.presenter.move_recording_to_project(row, target_project.id)


def _process_with_claude(gui: "WhisperGUI", row: int) -> None:
    """Process recording with Claude."""
    gui.presenter.selected_row = row
    gui.presenter.process_with_codex()
