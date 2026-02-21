"""Project sidebar widget for managing and selecting projects."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if False:  # pragma: no cover - for typing only
    from .presenter import WhisperPresenter


class ProjectSidebar(QWidget):
    """Sidebar widget for managing projects."""

    project_selected = pyqtSignal(str)  # Emits project_id when a project is selected

    def __init__(self, presenter: "WhisperPresenter", parent=None):
        super().__init__(parent)
        self.presenter = presenter
        self.is_collapsed = False

        self._init_ui()
        self._refresh_projects()

        # Connect to presenter signals
        self.presenter.projects_changed.connect(self._refresh_projects)

    def _init_ui(self) -> None:
        """Initialize the UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Project list
        self.project_list = QListWidget()
        self.project_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self._show_project_context_menu)
        self.project_list.itemClicked.connect(self._on_project_clicked)
        layout.addWidget(self.project_list)

        # New project button
        self.new_project_btn = QPushButton("+ New Project")
        self.new_project_btn.clicked.connect(self._create_new_project)
        self.new_project_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """
        )
        layout.addWidget(self.new_project_btn)

        # Toggle button
        self.toggle_btn = QPushButton("◀")
        self.toggle_btn.clicked.connect(self._toggle_sidebar)
        self.toggle_btn.setMaximumWidth(30)
        self.toggle_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #666;
                color: white;
                padding: 4px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #888;
            }
        """
        )
        layout.addWidget(self.toggle_btn)

        self.setLayout(layout)
        self.setMinimumWidth(200)
        self.setMaximumWidth(300)

    def _refresh_projects(self) -> None:
        """Refresh the project list."""
        self.project_list.clear()
        projects = self.presenter.project_manager.projects
        current_project = self.presenter.project_manager.current_project

        for project in projects:
            item = QListWidgetItem(project.name)
            item.setData(Qt.ItemDataRole.UserRole, project.id)

            # Highlight current project
            if current_project and project.id == current_project.id:
                item.setBackground(Qt.GlobalColor.lightGray)
                font = item.font()
                font.setBold(True)
                item.setFont(font)

            # Mark default project
            if project.is_default:
                item.setText(f"{project.name} 🏠")

            self.project_list.addItem(item)

    def _on_project_clicked(self, item: QListWidgetItem) -> None:
        """Handle project selection."""
        project_id = item.data(Qt.ItemDataRole.UserRole)
        self.presenter.project_manager.set_current_project(project_id)
        self._refresh_projects()
        self.project_selected.emit(project_id)
        self.presenter.history_changed.emit()

    def _create_new_project(self) -> None:
        """Create a new project."""
        name, ok = QInputDialog.getText(
            self,
            "New Project",
            "Enter project name:",
        )

        if ok and name:
            try:
                self.presenter.project_manager.create_project(name)
                self.presenter.projects_changed.emit()
                self.presenter.status_message.emit(f"✅ Created project: {name}")
            except ValueError as e:
                QMessageBox.warning(self, "Error", str(e))

    def _show_project_context_menu(self, position) -> None:
        """Show context menu for project management."""
        item = self.project_list.itemAt(position)
        if not item:
            return

        project_id = item.data(Qt.ItemDataRole.UserRole)
        project = self.presenter.project_manager.get_project(project_id)
        if not project:
            return

        menu = QMenu(self)

        # Rename action
        rename_action = menu.addAction("✏️ Rename")
        rename_action.triggered.connect(lambda: self._rename_project(project_id))

        # Delete action (disabled for default project)
        if not project.is_default:
            delete_action = menu.addAction("🗑️ Delete")
            delete_action.triggered.connect(lambda: self._delete_project(project_id))
        else:
            delete_action = menu.addAction("🗑️ Delete (Default project cannot be deleted)")
            delete_action.setEnabled(False)

        menu.exec(self.project_list.mapToGlobal(position))

    def _rename_project(self, project_id: str) -> None:
        """Rename a project."""
        project = self.presenter.project_manager.get_project(project_id)
        if not project:
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Project",
            "Enter new name:",
            text=project.name,
        )

        if ok and new_name:
            try:
                self.presenter.project_manager.rename_project(project_id, new_name)
                self.presenter.projects_changed.emit()
                self.presenter.status_message.emit(f"✅ Renamed project to: {new_name}")
            except ValueError as e:
                QMessageBox.warning(self, "Error", str(e))

    def _delete_project(self, project_id: str) -> None:
        """Delete a project."""
        project = self.presenter.project_manager.get_project(project_id)
        if not project:
            return

        reply = QMessageBox.question(
            self,
            "Delete Project",
            f"Are you sure you want to delete '{project.name}'?\n\n"
            "All recordings in this project will be moved to the default project.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Move all recordings to default project
            default_project = self.presenter.project_manager.get_default_project()
            if default_project:
                for item in self.presenter.history:
                    if item.get("project_id") == project_id:
                        item["project_id"] = default_project.id
                self.presenter._save_history()

            # Delete the project
            self.presenter.project_manager.delete_project(project_id)
            self.presenter.projects_changed.emit()
            self.presenter.history_changed.emit()
            self.presenter.status_message.emit(f"🗑️ Deleted project: {project.name}")

    def _toggle_sidebar(self) -> None:
        """Toggle sidebar collapsed/expanded state."""
        if self.is_collapsed:
            # Expand
            self.project_list.show()
            self.new_project_btn.show()
            self.toggle_btn.setText("◀")
            self.setMinimumWidth(200)
            self.setMaximumWidth(300)
            self.is_collapsed = False
        else:
            # Collapse
            self.project_list.hide()
            self.new_project_btn.hide()
            self.toggle_btn.setText("▶")
            self.setMinimumWidth(30)
            self.setMaximumWidth(30)
            self.is_collapsed = True


__all__ = ["ProjectSidebar"]
