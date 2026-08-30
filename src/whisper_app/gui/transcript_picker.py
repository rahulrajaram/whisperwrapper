"""Keyboard-first picker for past Whisper transcripts."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..recipes import Recipe, matching_recipes

X11_TIMEOUT_SECONDS = 2


@dataclass(frozen=True)
class TranscriptChoice:
    timestamp: str
    text: str
    project_id: str | None


def transcript_choices(
    history: Sequence[Mapping[str, object]],
) -> tuple[TranscriptChoice, ...]:
    return tuple(
        TranscriptChoice(
            timestamp=str(item.get("timestamp", "")),
            text=text,
            project_id=(str(item["project_id"]) if item.get("project_id") is not None else None),
        )
        for item in history
        if (text := str(item.get("text", "")).strip())
    )


def matching_transcripts(
    choices: Sequence[TranscriptChoice],
    query: str,
) -> tuple[TranscriptChoice, ...]:
    terms = tuple(query.casefold().split())
    return tuple(
        choice
        for choice in choices
        if all(term in f"{choice.timestamp} {choice.text}".casefold() for term in terms)
    )


def transcript_preview(text: str, limit: int = 180) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else f"{normalized[:limit - 1]}…"


def active_x11_window() -> str | None:
    try:
        result = subprocess.run(
            ("xdotool", "getactivewindow"),
            check=True,
            capture_output=True,
            text=True,
            timeout=X11_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    window_id = result.stdout.strip()
    return window_id if window_id.isdigit() else None


def activate_x11_window(window_id: str | None) -> bool:
    if window_id is None or not window_id.isdigit():
        return False
    try:
        subprocess.run(
            ("xdotool", "windowactivate", "--sync", window_id),
            check=True,
            capture_output=True,
            text=True,
            timeout=X11_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    return True


def x11_window_exists(window_id: str | None) -> bool:
    if window_id is None or not window_id.isdigit():
        return False
    try:
        subprocess.run(
            ("xdotool", "getwindowname", window_id),
            check=True,
            capture_output=True,
            text=True,
            timeout=X11_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    return True


def paste_primary_selection() -> bool:
    try:
        subprocess.run(
            ("xdotool", "key", "shift+Insert"),
            check=True,
            capture_output=True,
            text=True,
            timeout=X11_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    return True


class TranscriptPicker(QDialog):
    paste_requested = pyqtSignal(str)
    copy_requested = pyqtSignal(str)
    recipe_requested = pyqtSignal(str)

    def __init__(
        self,
        choices: Sequence[TranscriptChoice],
        recipes: Sequence[Recipe] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._choices = tuple(choices)
        self._visible_choices = self._choices
        self._recipes = tuple(recipes)
        self._visible_recipes = self._recipes
        self.setWindowTitle("Whisper transcripts and recipes")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setModal(False)
        self.resize(920, 620)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        transcript_page = QWidget()
        transcript_layout = QVBoxLayout(transcript_page)
        transcript_layout.addWidget(QLabel("Choose a past transcript"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Type to filter transcripts…")
        transcript_layout.addWidget(self.search)
        self.results = QListWidget()
        transcript_layout.addWidget(self.results)
        self.tabs.addTab(transcript_page, "Transcript History")

        recipe_page = QWidget()
        recipe_layout = QVBoxLayout(recipe_page)
        recipe_layout.addWidget(QLabel("Choose a recipe to run in a new XFCE Terminal"))
        self.recipe_search = QLineEdit()
        self.recipe_search.setPlaceholderText("Type to filter recipes by name or keyword…")
        recipe_layout.addWidget(self.recipe_search)
        self.recipe_results = QListWidget()
        recipe_layout.addWidget(self.recipe_results)
        self.tabs.addTab(recipe_page, "Recipes")

        layout.addWidget(
            QLabel(
                "Tab or 4/6 switch views · 8/2 navigate · 9/3 page · "
                "Enter choose · Ctrl+C copy transcript · Escape cancel"
            )
        )

        self.search.textChanged.connect(self._refilter)
        self.recipe_search.textChanged.connect(self._refilter_recipes)
        self.results.itemActivated.connect(lambda _item: self._choose_current(paste=True))
        self.recipe_results.itemActivated.connect(lambda _item: self._choose_current(paste=True))
        self.tabs.currentChanged.connect(lambda _index: self._focus_current_search())
        for watched in (
            self,
            self.tabs,
            self.search,
            self.results,
            self.recipe_search,
            self.recipe_results,
        ):
            watched.installEventFilter(self)
        self._render(self._visible_choices)
        self._render_recipes(self._visible_recipes)
        self.tabs.setCurrentIndex(0 if self._choices else 1)
        self._focus_current_search()

    def _render(self, choices: Sequence[TranscriptChoice]) -> None:
        self.results.clear()
        for choice in choices:
            item = QListWidgetItem(f"{choice.timestamp}  ·  {transcript_preview(choice.text)}")
            self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(0)

    def _refilter(self, query: str) -> None:
        self._visible_choices = matching_transcripts(self._choices, query)
        self._render(self._visible_choices)

    def _render_recipes(self, recipes: Sequence[Recipe]) -> None:
        self.recipe_results.clear()
        for recipe in recipes:
            self.recipe_results.addItem(QListWidgetItem(f"{recipe.title}  ·  {recipe.description}"))
        if self.recipe_results.count():
            self.recipe_results.setCurrentRow(0)

    def _refilter_recipes(self, query: str) -> None:
        self._visible_recipes = matching_recipes(self._recipes, query)
        self._render_recipes(self._visible_recipes)

    def _active_results(self) -> QListWidget:
        return self.results if self.tabs.currentIndex() == 0 else self.recipe_results

    def _focus_current_search(self) -> None:
        search = self.search if self.tabs.currentIndex() == 0 else self.recipe_search
        search.setFocus()

    def _move(self, amount: int) -> None:
        results = self._active_results()
        count = results.count()
        if count == 0:
            return
        current = max(results.currentRow(), 0)
        results.setCurrentRow(min(max(current + amount, 0), count - 1))

    def _switch_tab(self, amount: int) -> None:
        self.tabs.setCurrentIndex((self.tabs.currentIndex() + amount) % self.tabs.count())
        self._focus_current_search()

    def _current_choice(self) -> TranscriptChoice | None:
        row = self.results.currentRow()
        return self._visible_choices[row] if 0 <= row < len(self._visible_choices) else None

    def _choose_transcript(self, *, paste: bool) -> None:
        choice = self._current_choice()
        if choice is None:
            return
        self.accept()
        signal = self.paste_requested if paste else self.copy_requested
        signal.emit(choice.text)

    def _current_recipe(self) -> Recipe | None:
        row = self.recipe_results.currentRow()
        return self._visible_recipes[row] if 0 <= row < len(self._visible_recipes) else None

    def _choose_recipe(self) -> None:
        recipe = self._current_recipe()
        if recipe is None:
            return
        self.accept()
        self.recipe_requested.emit(recipe.recipe_id)

    def _choose_current(self, *, paste: bool) -> None:
        if self.tabs.currentIndex() == 0:
            self._choose_transcript(paste=paste)
        elif paste:
            self._choose_recipe()

    def eventFilter(self, watched, event):  # pragma: no cover - Qt dispatch wrapper
        if event.type() != QEvent.Type.KeyPress:
            return super().eventFilter(watched, event)

        key = event.key()
        modifiers = event.modifiers()
        keypad = bool(modifiers & Qt.KeyboardModifier.KeypadModifier)
        control = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        if key == Qt.Key.Key_Tab:
            direction = -1 if modifiers & Qt.KeyboardModifier.ShiftModifier else 1
            self._switch_tab(direction)
            return True
        if control and key == Qt.Key.Key_PageUp:
            self._switch_tab(-1)
            return True
        if control and key == Qt.Key.Key_PageDown:
            self._switch_tab(1)
            return True
        if key == Qt.Key.Key_Up or (keypad and key == Qt.Key.Key_8):
            self._move(-1)
            return True
        if key == Qt.Key.Key_Down or (keypad and key == Qt.Key.Key_2):
            self._move(1)
            return True
        if key == Qt.Key.Key_PageUp or (keypad and key == Qt.Key.Key_9):
            self._move(-8)
            return True
        if key == Qt.Key.Key_PageDown or (keypad and key == Qt.Key.Key_3):
            self._move(8)
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._choose_current(paste=True)
            return True
        if key == Qt.Key.Key_C and control and self.tabs.currentIndex() == 0:
            self._choose_current(paste=False)
            return True
        if key == Qt.Key.Key_Escape:
            self.reject()
            return True
        return super().eventFilter(watched, event)


__all__ = [
    "TranscriptChoice",
    "TranscriptPicker",
    "activate_x11_window",
    "active_x11_window",
    "matching_transcripts",
    "paste_primary_selection",
    "transcript_choices",
    "transcript_preview",
    "x11_window_exists",
]
