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
    history = gui.presenter.history
    table.setRowCount(len(history))

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
