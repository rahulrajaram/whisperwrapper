"""Project management for organizing recordings."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ..config import WhisperPaths


@dataclass
class Project:
    """A project for organizing recordings."""

    id: str
    name: str
    created_at: str
    is_default: bool = False

    def __post_init__(self):
        """Validate project data."""
        if not self.name:
            raise ValueError("Project name cannot be empty")


class ProjectManager:
    """Manages projects and their persistence."""

    def __init__(self, paths: WhisperPaths):
        self.paths = paths
        self.paths.base_dir.mkdir(parents=True, exist_ok=True)
        self._projects: List[Project] = []
        self._current_project_id: Optional[str] = None
        self._load()

    @property
    def projects_path(self) -> Path:
        """Path to the projects JSON file."""
        return self.paths.base_dir / "projects.json"

    @property
    def projects(self) -> List[Project]:
        """Get all projects."""
        return self._projects.copy()

    @property
    def current_project(self) -> Optional[Project]:
        """Get the currently selected project."""
        if self._current_project_id:
            return self.get_project(self._current_project_id)
        return None

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        for project in self._projects:
            if project.id == project_id:
                return project
        return None

    def get_default_project(self) -> Optional[Project]:
        """Get the default project."""
        for project in self._projects:
            if project.is_default:
                return project
        return None

    def create_project(self, name: str, is_default: bool = False) -> Project:
        """Create a new project.

        Args:
            name: Project name
            is_default: Whether this is the default project

        Returns:
            The newly created project

        Raises:
            ValueError: If a project with the same name already exists
        """
        # Check for duplicate names
        if any(p.name == name for p in self._projects):
            raise ValueError(f"Project '{name}' already exists")

        from datetime import datetime
        project = Project(
            id=str(uuid.uuid4()),
            name=name,
            created_at=datetime.now().isoformat(),
            is_default=is_default,
        )
        self._projects.append(project)
        self._save()

        # If this is the first project or explicitly default, set as current
        if len(self._projects) == 1 or is_default:
            self._current_project_id = project.id
            self._save()

        return project

    def rename_project(self, project_id: str, new_name: str) -> bool:
        """Rename a project.

        Args:
            project_id: ID of the project to rename
            new_name: New name for the project

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If new name is empty or already exists
        """
        if not new_name:
            raise ValueError("Project name cannot be empty")

        # Check for duplicate names (excluding current project)
        if any(p.name == new_name and p.id != project_id for p in self._projects):
            raise ValueError(f"Project '{new_name}' already exists")

        project = self.get_project(project_id)
        if not project:
            return False

        project.name = new_name
        self._save()
        return True

    def delete_project(self, project_id: str) -> bool:
        """Delete a project.

        Args:
            project_id: ID of the project to delete

        Returns:
            True if successful, False otherwise

        Note:
            Cannot delete the default project. If deleting the current project,
            switches to the default project.
        """
        project = self.get_project(project_id)
        if not project:
            return False

        # Cannot delete default project
        if project.is_default:
            return False

        self._projects = [p for p in self._projects if p.id != project_id]

        # If deleting current project, switch to default
        if self._current_project_id == project_id:
            default = self.get_default_project()
            self._current_project_id = default.id if default else None

        self._save()
        return True

    def set_current_project(self, project_id: str) -> bool:
        """Set the current project.

        Args:
            project_id: ID of the project to set as current

        Returns:
            True if successful, False if project not found
        """
        if not self.get_project(project_id):
            return False

        self._current_project_id = project_id
        self._save()
        return True

    def _load(self) -> None:
        """Load projects from disk."""
        try:
            if self.projects_path.exists():
                data = json.loads(self.projects_path.read_text())
                self._projects = [
                    Project(
                        id=p["id"],
                        name=p["name"],
                        created_at=p["created_at"],
                        is_default=p.get("is_default", False),
                    )
                    for p in data.get("projects", [])
                ]
                self._current_project_id = data.get("current_project_id")
            else:
                # Create default project on first run
                from datetime import datetime
                default_project = Project(
                    id=str(uuid.uuid4()),
                    name="General",
                    created_at=datetime.now().isoformat(),
                    is_default=True,
                )
                self._projects = [default_project]
                self._current_project_id = default_project.id
                self._save()
        except Exception:
            # If loading fails, create default project
            from datetime import datetime
            default_project = Project(
                id=str(uuid.uuid4()),
                name="General",
                created_at=datetime.now().isoformat(),
                is_default=True,
            )
            self._projects = [default_project]
            self._current_project_id = default_project.id
            self._save()

    def _save(self) -> None:
        """Save projects to disk."""
        try:
            self.projects_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "projects": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "created_at": p.created_at,
                        "is_default": p.is_default,
                    }
                    for p in self._projects
                ],
                "current_project_id": self._current_project_id,
            }
            self.projects_path.write_text(json.dumps(data, indent=2))
        except Exception:
            pass


__all__ = ["Project", "ProjectManager"]
