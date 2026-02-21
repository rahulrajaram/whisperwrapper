"""Helpers for rendering the history table."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QLabel, QPushButton, QTableWidgetItem

if False:  # pragma: no cover - for typing only
    from .main_window import WhisperGUI

from .utils import markdown_to_html

# Selection highlight color (light blue)
SELECTED_ROW_COLOR = QColor(200, 220, 255)


class ClickableLabel(QLabel):
    clicked = pyqtSignal(int, bool, bool)  # row, shift, ctrl
    right_clicked = pyqtSignal(int)  # row

    def __init__(self, text: str, row_index: int, parent=None):
        super().__init__(text, parent)
        self.row_index = row_index

    def mousePressEvent(self, event):  # pragma: no cover - Qt event hook
        if event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self.row_index)
            return

        shift = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ctrl = event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)
        self.clicked.emit(self.row_index, bool(shift), bool(ctrl))
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
        # Apply row background color if selected
        is_selected = row in gui.presenter.selected_rows
        row_bg_color = SELECTED_ROW_COLOR if is_selected else Qt.GlobalColor.white

        # Create timestamp item
        timestamp_item = QTableWidgetItem(item.get("timestamp", ""))
        timestamp_item.setFlags(timestamp_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        timestamp_item.setBackground(row_bg_color)
        table.setItem(row, 0, timestamp_item)

        # Create text label with background color applied
        html_text = markdown_to_html(item.get("text", ""))
        text_label = ClickableLabel(html_text, row)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        # Apply background color to the label itself
        if is_selected:
            text_label.setStyleSheet(f"background-color: rgb(200, 220, 255);")
        else:
            text_label.setStyleSheet("background-color: white;")

        # Connect to multi-select handler with shift/ctrl modifiers
        text_label.clicked.connect(lambda r, shift, ctrl: gui.presenter.select_row(r, shift, ctrl))
        # Connect to right-click handler
        text_label.right_clicked.connect(lambda r: _on_row_right_clicked(gui, r))
        table.setCellWidget(row, 1, text_label)

    # Update status message
    if gui.presenter.selected_rows:
        selection_count = len(gui.presenter.selected_rows)
        gui.statusBar().showMessage(f"History updated - {selection_count} row(s) selected")
    else:
        gui.statusBar().showMessage("History updated")


def _on_row_right_clicked(gui: "WhisperGUI", row: int) -> None:
    """Handle right-click on a row from the label widget."""
    from PyQt6.QtGui import QCursor
    from PyQt6.QtCore import QPoint

    # Get the global cursor position for the context menu
    cursor_pos = QCursor.pos()
    # Convert to table viewport coordinates
    table = gui.history_table
    viewport_pos = table.viewport().mapFromGlobal(cursor_pos)

    # Show context menu at cursor position
    _show_recording_context_menu(gui, viewport_pos)


def _show_recording_context_menu(gui: "WhisperGUI", position) -> None:
    """Show context menu for recording operations."""
    from PyQt6.QtWidgets import QMenu

    table = gui.history_table
    row = table.rowAt(position.y())
    if row < 0:
        return

    menu = QMenu(gui)

    # Check if we have multi-select
    is_multi_select = len(gui.presenter.selected_rows) > 1

    # Copy action - only available for single selection (highlighted)
    copy_action = menu.addAction("📋 Copy to Clipboard")
    copy_action.triggered.connect(lambda: gui.presenter.copy_to_clipboard(row))
    if is_multi_select:
        copy_action.setEnabled(False)
    else:
        copy_action.setText("📋 Copy to Clipboard")

    # Copy to Project action - available for both single and multi-select
    if is_multi_select:
        copy_project_action = menu.addAction("📋 Copy to Project (Selected)")
        copy_project_action.triggered.connect(lambda: _copy_selected_to_project(gui))
    else:
        copy_project_action = menu.addAction("📋 Copy to Project")
        copy_project_action.triggered.connect(lambda: _copy_recording_to_project(gui, row))

    # Move action - available for both single and multi-select
    if is_multi_select:
        move_action = menu.addAction("➡️ Move to Project (Selected)")
        move_action.triggered.connect(lambda: _move_selected_to_project(gui))
    else:
        move_action = menu.addAction("➡️ Move to Project")
        move_action.triggered.connect(lambda: _move_recording_to_project(gui, row))

    menu.addSeparator()

    # Toggle protection action - works on single or multiple selections
    if is_multi_select:
        lock_action = menu.addAction("🔒 Toggle Protection (Selected)")
        lock_action.triggered.connect(lambda: gui.presenter.toggle_protection_selected())
    else:
        is_protected = gui.presenter.history[row].get("protected", False)
        lock_action = menu.addAction(f"{'🔓' if is_protected else '🔒'} Toggle Protection")
        lock_action.triggered.connect(lambda: gui.presenter.toggle_protection(row))

    # Delete action - works on single or multiple selections
    if is_multi_select:
        delete_action = menu.addAction("🗑️ Delete (Selected)")
        delete_action.triggered.connect(lambda: gui.presenter.delete_selected())
    else:
        delete_action = menu.addAction("🗑️ Delete")
        delete_action.triggered.connect(lambda: gui.presenter.delete_history_item(row))

    menu.addSeparator()

    # Process with Claude action - only for single selection
    process_action = menu.addAction("🤖 Process with Claude")
    process_action.triggered.connect(lambda: _process_with_claude(gui, row))
    if is_multi_select:
        process_action.setEnabled(False)

    menu.exec(table.viewport().mapToGlobal(position))


def _copy_selected_to_project(gui: "WhisperGUI") -> None:
    """Copy all selected recordings to another project."""
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
            gui.presenter.copy_selected_to_project(target_project.id)


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


def _move_selected_to_project(gui: "WhisperGUI") -> None:
    """Move all selected recordings to another project."""
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
            gui.presenter.move_selected_to_project(target_project.id)


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
