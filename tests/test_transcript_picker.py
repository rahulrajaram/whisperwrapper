"""Regression tests for the keyboard-driven transcript clipboard."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from whisper_app.recipes import Recipe
from whisper_app.gui.transcript_picker import (
    TranscriptPicker,
    matching_transcripts,
    transcript_choices,
    transcript_preview,
    x11_window_exists,
)


def recipe(recipe_id: str, title: str) -> Recipe:
    return Recipe(
        recipe_id=recipe_id,
        title=title,
        description=f"Run {title}",
        keywords=("deepmetrics",),
        working_directory=Path("/tmp"),
        commands=(("true",),),
    )


def test_transcript_choices_are_immutable_and_skip_empty_text() -> None:
    history = [
        {"timestamp": "new", "text": " alpha ", "project_id": "p1"},
        {"timestamp": "empty", "text": "   ", "project_id": "p2"},
    ]

    choices = transcript_choices(history)

    assert len(choices) == 1
    assert choices[0].text == "alpha"
    assert choices[0].project_id == "p1"


def test_matching_transcripts_requires_every_case_insensitive_term() -> None:
    choices = transcript_choices(
        [
            {"timestamp": "2026-08-27", "text": "Alpha beta"},
            {"timestamp": "2026-08-26", "text": "Alpha gamma"},
        ]
    )

    assert matching_transcripts(choices, "ALPHA 27") == (choices[0],)
    assert matching_transcripts(choices, "missing") == ()


def test_transcript_preview_normalizes_and_truncates() -> None:
    assert transcript_preview("alpha\n  beta", limit=20) == "alpha beta"
    assert transcript_preview("abcdefghij", limit=6) == "abcde…"


def test_x11_window_exists_rejects_invalid_ids_without_a_subprocess() -> None:
    assert x11_window_exists(None) is False
    assert x11_window_exists("not-a-window") is False


def test_picker_navigates_and_selects_with_the_keyboard(qt_app) -> None:
    choices = transcript_choices(
        [
            {"timestamp": "1", "text": "first"},
            {"timestamp": "2", "text": "second"},
        ]
    )
    picker = TranscriptPicker(choices)
    selected: list[str] = []
    picker.paste_requested.connect(selected.append)
    picker.show()

    QApplication.sendEvent(
        picker.search,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier),
    )
    QApplication.sendEvent(
        picker.search,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier),
    )

    assert selected == ["second"]
    assert picker.result() == TranscriptPicker.DialogCode.Accepted


def test_picker_switches_to_searchable_recipes_and_emits_selection(qt_app) -> None:
    choices = transcript_choices([{"timestamp": "1", "text": "transcript"}])
    recipes = (
        recipe("develop", "Continue development"),
        recipe("health", "System health summary"),
    )
    picker = TranscriptPicker(choices, recipes)
    selected: list[str] = []
    picker.recipe_requested.connect(selected.append)
    picker.show()

    QApplication.sendEvent(
        picker.search,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier),
    )
    picker.recipe_search.setText("health deepmetrics")
    QApplication.sendEvent(
        picker.recipe_search,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier),
    )

    assert picker.tabs.currentIndex() == 1
    assert selected == ["health"]
    assert picker.result() == TranscriptPicker.DialogCode.Accepted


def test_picker_accepts_macropad_tab_chords(qt_app) -> None:
    picker = TranscriptPicker(
        transcript_choices([{"timestamp": "1", "text": "transcript"}]),
        (recipe("health", "System health summary"),),
    )
    picker.show()

    QApplication.sendEvent(
        picker.search,
        QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_PageDown,
            Qt.KeyboardModifier.ControlModifier,
        ),
    )
    assert picker.tabs.currentIndex() == 1

    QApplication.sendEvent(
        picker.recipe_search,
        QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_PageUp,
            Qt.KeyboardModifier.ControlModifier,
        ),
    )
    assert picker.tabs.currentIndex() == 0
