"""Presenter/ViewModel layer that mediates between PyQt widgets and controllers."""

from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime
from typing import List, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ..controllers import WhisperRecordingController
from .config import GUIStorageManager
from .projects import ProjectManager
from .workers import CodexWorker, RecordingWorker


class WhisperPresenter(QObject):
    """
    Presenter responsible for orchestrating recording/codex workflows and
    persisting UI state so widgets remain mostly declarative.
    """

    recording_started = pyqtSignal()
    recording_finished = pyqtSignal()
    recording_status = pyqtSignal(str)
    recording_error = pyqtSignal(str)
    transcription_ready = pyqtSignal(str)

    history_changed = pyqtSignal()
    status_message = pyqtSignal(str)

    codex_started = pyqtSignal()
    codex_finished = pyqtSignal()
    codex_error = pyqtSignal(str)

    projects_changed = pyqtSignal()

    def __init__(
        self,
        recording_controller: WhisperRecordingController,
        storage: GUIStorageManager,
        project_manager: ProjectManager,
    ) -> None:
        super().__init__()
        self.recording_controller = recording_controller
        self.storage = storage
        self.project_manager = project_manager

        self.history: List[dict] = self.storage.load_history() or []
        self.selected_row: Optional[int] = None
        self.selected_rows: set[int] = set()  # For multi-select support
        self.last_selected_row: Optional[int] = None  # For shift-click range selection

        self.is_recording = False
        self._recording_thread: Optional[QThread] = None
        self._recording_worker: Optional[RecordingWorker] = None

        self._codex_thread: Optional[QThread] = None
        self._codex_worker: Optional[CodexWorker] = None

        # Migrate existing recordings to default project if needed
        self._migrate_recordings_to_projects()

    # ---------------------------------------------------------------------
    # Recording lifecycle
    # ---------------------------------------------------------------------

    def start_recording(self) -> bool:
        """Kick off recording via the worker thread."""
        if self.is_recording:
            self.status_message.emit("⚠️ Already recording...")
            return False

        self.is_recording = True
        self._recording_worker = RecordingWorker(self.recording_controller)
        self._recording_thread = QThread()
        self._recording_worker.moveToThread(self._recording_thread)
        self._recording_thread.started.connect(self._recording_worker.run)
        self._recording_worker.finished.connect(self._on_recording_finished)
        self._recording_worker.result.connect(self._on_recording_result)
        self._recording_worker.error.connect(self._on_recording_error)
        self._recording_worker.status_update.connect(self.recording_status.emit)

        self.recording_started.emit()
        self._recording_thread.start()
        return True

    def stop_recording(self) -> None:
        """Signal the worker to stop and begin processing."""
        if not self.is_recording or not self._recording_worker:
            return

        self._recording_worker.stop()
        self.status_message.emit("⏳ Processing transcription...")

    def wait_for_recording(self, timeout_ms: int = 5000) -> None:
        """Block until the current recording worker shuts down.

        Args:
            timeout_ms: Maximum time to wait in milliseconds (default: 5000ms = 5 seconds)
        """
        if self._recording_thread:
            if self._recording_thread.isRunning():
                self._recording_thread.quit()
                # Use wait() with timeout to prevent indefinite blocking
                # Try with timeout first (real QThread supports it), fall back to no timeout (for mocks)
                try:
                    result = self._recording_thread.wait(timeout_ms)
                    if not result:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning("Recording thread did not exit within %dms timeout", timeout_ms)
                except TypeError:
                    # Mock/fake thread doesn't support timeout parameter
                    self._recording_thread.wait()
            self._recording_thread = None

    def shutdown(self) -> None:
        """Ensure background workers are stopped when the app exits."""
        import logging
        logger = logging.getLogger(__name__)

        if self.is_recording:
            logger.debug("Stopping active recording before shutdown...")
            self.stop_recording()

        logger.debug("Waiting for recording thread to finish...")
        self.wait_for_recording(timeout_ms=5000)

        if self._codex_thread and self._codex_thread.isRunning():
            logger.debug("Stopping codex thread...")
            self._codex_thread.quit()
            # Add timeout to codex thread wait as well
            if not self._codex_thread.wait(5000):  # 5 second timeout
                logger.warning("Codex thread did not exit within 5s timeout")

        logger.debug("Presenter shutdown complete")

    # ------------------------------------------------------------------
    # History helpers
    # ------------------------------------------------------------------

    def copy_to_clipboard(self, row: int) -> None:
        """Copy a history row to clipboard selections."""
        if row >= len(self.history):
            return
        text = self.history[row]["text"]
        if self._copy_text_to_clipboard(text):
            preview = text[:40]
            self.status_message.emit(f"✅ Copied to clipboard: {preview}...")

    def toggle_protection(self, row: int) -> None:
        if row >= len(self.history):
            return
        item = self.history[row]
        item["protected"] = not item.get("protected", False)
        self._save_history()
        status = "🔒 Protected" if item["protected"] else "🔓 Unprotected"
        text_preview = item["text"][:40]
        self.status_message.emit(f"{status}: {text_preview}...")
        self.history_changed.emit()

    def toggle_row_selection(self, row: int) -> Optional[int]:
        """Toggle selection state; returns the new selection."""
        if self.selected_row == row:
            self.selected_row = None
        else:
            self.selected_row = row
        return self.selected_row

    def delete_history_item(self, row: int) -> None:
        if row >= len(self.history):
            return
        deleted_item = self.history.pop(row)
        self._save_history()
        self.selected_row = None
        self.history_changed.emit()
        text_preview = deleted_item["text"][:40]
        self.status_message.emit(f"🗑 Deleted: {text_preview}...")

    def clear_history(self) -> None:
        """Clear history for the current project only, preserving protected items."""
        current_project = self.project_manager.current_project
        if not current_project:
            self.status_message.emit("❌ No project selected")
            return

        # Separate items: keep protected items and items from other projects
        project_id = current_project.id
        items_to_keep = [
            item
            for item in self.history
            if item.get("protected", False) or item.get("project_id") != project_id
        ]

        # Count what we're deleting
        deleted_count = len(self.history) - len(items_to_keep)

        self.history = items_to_keep
        self._save_history()
        self.selected_row = None
        self.history_changed.emit()

        if deleted_count > 0:
            protected_in_project = sum(
                1
                for item in self.history
                if item.get("protected", False) and item.get("project_id") == project_id
            )
            if protected_in_project > 0:
                self.status_message.emit(
                    f"🗑 Deleted {deleted_count} items ({protected_in_project} protected in {current_project.name})"
                )
            else:
                self.status_message.emit(
                    f"🗑 {current_project.name} history cleared"
                )
        else:
            self.status_message.emit(
                f"🔒 All items in {current_project.name} are protected"
            )

    # ------------------------------------------------------------------
    # Codex processing
    # ------------------------------------------------------------------

    def process_with_codex(self) -> None:
        """Run Claude post-processing on the selected/latest transcription."""
        if not self.history:
            self.status_message.emit("❌ No transcriptions to process")
            return

        row = self.selected_row if self.selected_row is not None else 0
        row = min(row, len(self.history) - 1)
        text_to_process = self.history[row]["text"]

        self._codex_worker = CodexWorker(text_to_process, row)
        self._codex_thread = QThread()
        self._codex_worker.moveToThread(self._codex_thread)
        self._codex_thread.started.connect(self._codex_worker.run)
        self._codex_worker.finished.connect(self._on_codex_finished)
        self._codex_worker.result.connect(self._on_codex_result)
        self._codex_worker.error.connect(self._on_codex_error)

        self.codex_started.emit()
        self._codex_thread.start()

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_recording_finished(self) -> None:
        self.is_recording = False
        self.recording_finished.emit()
        self.wait_for_recording()
        self._recording_worker = None

    def _on_recording_result(self, transcription: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        transcription_text = transcription.strip()

        # Get current project ID
        current_project = self.project_manager.current_project
        project_id = current_project.id if current_project else None

        self.history.insert(
            0,
            {
                "timestamp": timestamp,
                "text": transcription_text,
                "protected": False,
                "project_id": project_id,
            },
        )
        self._save_history()
        self.selected_row = None
        self._copy_text_to_clipboard(transcription_text)
        self._auto_paste()
        self.transcription_ready.emit(transcription_text)
        self.history_changed.emit()

    def _on_recording_error(self, message: str) -> None:
        self.is_recording = False
        self.recording_error.emit(message)
        self.status_message.emit(f"❌ Error: {message}")

    def _on_codex_result(self, processed_text: str, row_index: int) -> None:
        if row_index < len(self.history):
            self.history[row_index]["text"] = processed_text
            self._save_history()
            self.history_changed.emit()
        self._copy_text_to_clipboard(processed_text)
        self.transcription_ready.emit(processed_text)

    def _on_codex_error(self, error_msg: str) -> None:
        self.codex_error.emit(error_msg)
        self.status_message.emit(f"❌ Claude error: {error_msg}")

    def _on_codex_finished(self) -> None:
        self.codex_finished.emit()
        if self._codex_thread:
            self._codex_thread.quit()
            self._codex_thread.wait()
            self._codex_thread = None
        self._codex_worker = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _save_history(self) -> None:
        self.storage.save_history(self.history)

    def _copy_text_to_clipboard(self, text: str) -> bool:
        """Copy text to clipboard selections based on compositor."""
        try:
            if os.environ.get("WAYLAND_DISPLAY"):
                process = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE, text=True)
                process.communicate(input=text)
            else:
                for selection in ("primary", "clipboard"):
                    process = subprocess.Popen(
                        ["xclip", "-selection", selection],
                        stdin=subprocess.PIPE,
                        text=True,
                    )
                    process.communicate(input=text)
            return True
        except FileNotFoundError:
            self.status_message.emit("❌ Clipboard tool not found (wl-copy or xclip)")
            return False
        except Exception as exc:  # pragma: no cover - best-effort logging
            self.status_message.emit(f"❌ Copy failed: {exc}")
            return False

    def _auto_paste(self) -> None:
        """Attempt to auto-paste using common key combos."""
        try:
            display = os.environ.get("DISPLAY", "NOT SET")
            xauth = os.environ.get("XAUTHORITY", "NOT SET")
            print(f"🔍 Auto-paste X11 env: DISPLAY={display}, XAUTHORITY={xauth}")
            time.sleep(0.2)
            paste_methods = [
                (["xdotool", "key", "shift+Insert"], "Shift+Insert"),
                (["xdotool", "key", "ctrl+v"], "Ctrl+V"),
                (["xdotool", "key", "ctrl+shift+v"], "Ctrl+Shift+V"),
            ]
            for cmd, method_name in paste_methods:
                try:
                    result = subprocess.run(
                        cmd,
                        check=False,
                        timeout=1,
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        print(f"📋 Auto-pasted with {method_name}")
                        return
                except subprocess.TimeoutExpired:
                    continue
            print("⚠️ All paste methods failed (window may not have focus)")
        except Exception as exc:
            print(f"⚠️ Auto-paste failed (non-critical): {exc}")

    # ------------------------------------------------------------------
    # Project management
    # ------------------------------------------------------------------

    def get_filtered_history(self, project_id: Optional[str] = None) -> List[dict]:
        """Get history items filtered by project.

        Args:
            project_id: Project ID to filter by. If None, returns current project's items.

        Returns:
            List of history items for the specified project
        """
        if project_id is None:
            current_project = self.project_manager.current_project
            project_id = current_project.id if current_project else None

        if project_id is None:
            return self.history

        return [item for item in self.history if item.get("project_id") == project_id]

    def move_recording_to_project(self, row: int, target_project_id: str) -> None:
        """Move a recording to a different project.

        Args:
            row: Index of the recording in history
            target_project_id: ID of the target project
        """
        if row >= len(self.history):
            return

        if not self.project_manager.get_project(target_project_id):
            self.status_message.emit("❌ Target project not found")
            return

        self.history[row]["project_id"] = target_project_id
        self._save_history()
        self.history_changed.emit()
        self.status_message.emit("✅ Recording moved to project")

    def copy_recording_to_project(self, row: int, target_project_id: str) -> None:
        """Copy a recording to a different project.

        Args:
            row: Index of the recording in history
            target_project_id: ID of the target project
        """
        if row >= len(self.history):
            return

        if not self.project_manager.get_project(target_project_id):
            self.status_message.emit("❌ Target project not found")
            return

        # Create a copy of the recording with new project_id
        original = self.history[row]
        copy = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "text": original["text"],
            "protected": original.get("protected", False),
            "project_id": target_project_id,
        }
        self.history.insert(0, copy)
        self._save_history()
        self.history_changed.emit()
        self.status_message.emit("✅ Recording copied to project")

    def copy_selected_to_project(self, target_project_id: str) -> None:
        """Copy all selected recordings to a different project.

        Args:
            target_project_id: ID of the target project
        """
        if not self.project_manager.get_project(target_project_id):
            self.status_message.emit("❌ Target project not found")
            return

        if not self.selected_rows:
            return

        count = 0
        for row in sorted(self.selected_rows):
            if row >= len(self.history):
                continue
            original = self.history[row]
            copy = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "text": original["text"],
                "protected": original.get("protected", False),
                "project_id": target_project_id,
            }
            self.history.insert(0, copy)
            count += 1

        if count > 0:
            self._save_history()
            self.history_changed.emit()
            self.status_message.emit(f"✅ {count} recording(s) copied to project")

    def move_selected_to_project(self, target_project_id: str) -> None:
        """Move all selected recordings to a different project.

        Args:
            target_project_id: ID of the target project
        """
        if not self.project_manager.get_project(target_project_id):
            self.status_message.emit("❌ Target project not found")
            return

        if not self.selected_rows:
            return

        count = 0
        for row in sorted(self.selected_rows):
            if row >= len(self.history):
                continue
            self.history[row]["project_id"] = target_project_id
            count += 1

        if count > 0:
            self._save_history()
            self.history_changed.emit()
            self.status_message.emit(f"✅ {count} recording(s) moved to project")

    def _migrate_recordings_to_projects(self) -> None:
        """Migrate existing recordings without project_id to default project."""
        default_project = self.project_manager.get_default_project()
        if not default_project:
            return

        migrated = 0
        for item in self.history:
            if "project_id" not in item or item["project_id"] is None:
                item["project_id"] = default_project.id
                migrated += 1

        if migrated > 0:
            self._save_history()
            print(f"Migrated {migrated} recordings to default project")

    # ------------------------------------------------------------------
    # Multi-select support
    # ------------------------------------------------------------------

    def select_row(self, row: int, shift: bool = False, ctrl: bool = False) -> None:
        """
        Handle row selection with support for shift and ctrl/cmd clicks.

        Args:
            row: The row index to select
            shift: If True, select range from last_selected_row to row
            ctrl: If True, toggle selection of this row (add/remove)
        """
        if shift and self.last_selected_row is not None:
            # Shift-click: select range from last_selected_row to row
            start = min(self.last_selected_row, row)
            end = max(self.last_selected_row, row) + 1
            self.selected_rows.update(range(start, end))
        elif ctrl:
            # Ctrl-click: toggle selection
            if row in self.selected_rows:
                self.selected_rows.discard(row)
            else:
                self.selected_rows.add(row)
        else:
            # Regular click: select only this row
            self.selected_rows = {row}

        self.last_selected_row = row
        self.history_changed.emit()

    def clear_selection(self) -> None:
        """Clear all selected rows."""
        self.selected_rows.clear()
        self.last_selected_row = None
        self.history_changed.emit()

    def delete_selected(self) -> None:
        """Delete all selected items (respecting protected status)."""
        if not self.selected_rows:
            self.status_message.emit("❌ No items selected")
            return

        # Sort indices in descending order to avoid index shifting
        rows_to_delete = sorted(self.selected_rows, reverse=True)

        protected_count = 0
        deleted_count = 0

        for row in rows_to_delete:
            if row < len(self.history):
                if self.history[row].get("protected", False):
                    protected_count += 1
                else:
                    del self.history[row]
                    deleted_count += 1

        self._save_history()
        self.selected_rows.clear()
        self.last_selected_row = None
        self.history_changed.emit()

        if deleted_count > 0:
            if protected_count > 0:
                self.status_message.emit(
                    f"🗑 Deleted {deleted_count} items ({protected_count} protected)"
                )
            else:
                self.status_message.emit(f"🗑 Deleted {deleted_count} items")
        else:
            self.status_message.emit("🔒 All selected items are protected")

    def toggle_protection_selected(self) -> None:
        """Toggle protection status for all selected items."""
        if not self.selected_rows:
            self.status_message.emit("❌ No items selected")
            return

        protected_count = 0
        unprotected_count = 0

        for row in self.selected_rows:
            if row < len(self.history):
                is_protected = self.history[row].get("protected", False)
                self.history[row]["protected"] = not is_protected
                if not is_protected:
                    protected_count += 1
                else:
                    unprotected_count += 1

        self._save_history()
        self.history_changed.emit()

        if protected_count > 0 and unprotected_count > 0:
            self.status_message.emit(
                f"🔒 Protected {protected_count}, unprotected {unprotected_count}"
            )
        elif protected_count > 0:
            self.status_message.emit(f"🔒 Protected {protected_count} items")
        else:
            self.status_message.emit(f"🔓 Unprotected {unprotected_count} items")
