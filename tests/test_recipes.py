"""Tests for declarative launcher recipes."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from whisper_app import recipe_runner
from whisper_app.recipes import (
    Recipe,
    RecipeCatalogError,
    load_recipe_catalog,
    matching_recipes,
    plan_recipe_terminal,
    read_recipe_catalog,
)


def write_catalog(path: Path, recipes: list[dict[str, object]]) -> None:
    path.write_text(json.dumps({"recipes": recipes}), encoding="utf-8")


def recipe_payload(recipe_id: str, title: str) -> dict[str, object]:
    return {
        "id": recipe_id,
        "title": title,
        "description": "Inspect system health",
        "keywords": ["probe", "diagnostics"],
        "working_directory": "~/Documents/deepmetrics",
        "commands": [["venv/bin/python", "-m", "deepmetrics", "--summary"]],
    }


def test_catalog_is_typed_immutable_and_searchable(tmp_path: Path) -> None:
    path = tmp_path / "recipes.json"
    write_catalog(path, [recipe_payload("health", "DeepMetrics health")])

    recipes = read_recipe_catalog(path)

    assert recipes[0].commands == (("venv/bin/python", "-m", "deepmetrics", "--summary"),)
    assert matching_recipes(recipes, "deepmetrics diagnostics") == recipes
    assert matching_recipes(recipes, "missing") == ()


def test_user_catalog_overrides_packaged_recipe_by_id(tmp_path: Path) -> None:
    packaged = tmp_path / "packaged.json"
    user = tmp_path / "user.json"
    write_catalog(packaged, [recipe_payload("health", "Packaged health")])
    write_catalog(user, [recipe_payload("health", "Custom health")])

    recipes = load_recipe_catalog((packaged, user))

    assert tuple(recipe.title for recipe in recipes) == ("Custom health",)


def test_invalid_recipe_commands_fail_at_catalog_boundary(tmp_path: Path) -> None:
    path = tmp_path / "recipes.json"
    payload = recipe_payload("health", "DeepMetrics health")
    payload["commands"] = []
    write_catalog(path, [payload])

    with pytest.raises(RecipeCatalogError, match="at least one"):
        read_recipe_catalog(path)


def test_terminal_plan_runs_recipe_runner_in_a_new_held_window(tmp_path: Path) -> None:
    path = tmp_path / "recipes.json"
    write_catalog(path, [recipe_payload("health", "DeepMetrics health")])
    recipe = read_recipe_catalog(path)[0]

    plan = plan_recipe_terminal(recipe, "/venv/bin/python")

    assert plan.argv[:3] == ("/usr/bin/xfce4-terminal", "--window", "--hold")
    assert plan.argv[-4:] == (
        "/venv/bin/python",
        "-m",
        "whisper_app.recipe_runner",
        "health",
    )


def test_recipe_runner_executes_steps_in_order_and_stops_on_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    recipe = Recipe(
        recipe_id="steps",
        title="Steps",
        description="Sequential steps",
        keywords=(),
        working_directory=tmp_path,
        commands=(("first",), ("second",), ("never",)),
    )
    calls: list[tuple[tuple[str, ...], Path, bool]] = []
    return_codes = iter((0, 7))

    def run(command, *, cwd, check):
        calls.append((command, cwd, check))
        return SimpleNamespace(returncode=next(return_codes))

    monkeypatch.setattr(recipe_runner.subprocess, "run", run)

    assert recipe_runner.run_recipe(recipe) == 7
    assert calls == [
        (("first",), tmp_path, False),
        (("second",), tmp_path, False),
    ]
