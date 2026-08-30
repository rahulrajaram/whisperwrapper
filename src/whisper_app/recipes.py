"""Declarative, immutable recipes for the keyboard launcher."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


class RecipeCatalogError(ValueError):
    """Raised when a recipe catalog does not satisfy the public schema."""


@dataclass(frozen=True)
class Recipe:
    recipe_id: str
    title: str
    description: str
    keywords: tuple[str, ...]
    working_directory: Path
    commands: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class RecipeTerminalLaunch:
    argv: tuple[str, ...]


def _required_text(value: object, field: str) -> str:
    text = str(value).strip() if isinstance(value, str) else ""
    if not text:
        raise RecipeCatalogError(f"Recipe field '{field}' must be non-empty text")
    return text


def _string_sequence(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RecipeCatalogError(f"Recipe field '{field}' must be a list of strings")
    return tuple(item.strip() for item in value if item.strip())


def _commands(value: object) -> tuple[tuple[str, ...], ...]:
    if not isinstance(value, list):
        raise RecipeCatalogError("Recipe field 'commands' must be a list of argv lists")
    commands = tuple(_string_sequence(command, "commands[]") for command in value)
    if not commands or any(not command for command in commands):
        raise RecipeCatalogError("Every recipe must contain at least one non-empty command")
    return commands


def recipe_from_mapping(value: Mapping[str, object]) -> Recipe:
    recipe_id = _required_text(value.get("id"), "id")
    working_directory = Path(
        os.path.expandvars(
            os.path.expanduser(_required_text(value.get("working_directory"), "working_directory"))
        )
    )
    return Recipe(
        recipe_id=recipe_id,
        title=_required_text(value.get("title"), "title"),
        description=_required_text(value.get("description"), "description"),
        keywords=_string_sequence(value.get("keywords", []), "keywords"),
        working_directory=working_directory,
        commands=_commands(value.get("commands")),
    )


def read_recipe_catalog(path: Path) -> tuple[Recipe, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RecipeCatalogError(f"Could not read recipe catalog {path}: {error}") from error
    raw_recipes = payload.get("recipes") if isinstance(payload, dict) else None
    if not isinstance(raw_recipes, list):
        raise RecipeCatalogError(f"Recipe catalog {path} must contain a 'recipes' list")
    if not all(isinstance(item, dict) for item in raw_recipes):
        raise RecipeCatalogError(f"Every recipe in {path} must be an object")
    recipes = tuple(recipe_from_mapping(item) for item in raw_recipes)
    ids = tuple(recipe.recipe_id for recipe in recipes)
    if len(ids) != len(set(ids)):
        raise RecipeCatalogError(f"Recipe IDs must be unique within {path}")
    return recipes


def recipe_catalog_paths() -> tuple[Path, ...]:
    packaged = Path(__file__).with_name("recipes.json")
    configured = os.environ.get("WHISPER_RECIPE_CATALOG")
    user_catalog = (
        Path(os.path.expandvars(os.path.expanduser(configured)))
        if configured
        else Path.home() / ".config" / "whisper" / "recipes.json"
    )
    return packaged, user_catalog


def merge_recipe_catalogs(catalogs: Sequence[Sequence[Recipe]]) -> tuple[Recipe, ...]:
    return tuple({recipe.recipe_id: recipe for catalog in catalogs for recipe in catalog}.values())


def load_recipe_catalog(paths: Sequence[Path] | None = None) -> tuple[Recipe, ...]:
    candidates = tuple(paths) if paths is not None else recipe_catalog_paths()
    return merge_recipe_catalogs(
        tuple(read_recipe_catalog(path) for path in candidates if path.is_file())
    )


def matching_recipes(recipes: Sequence[Recipe], query: str) -> tuple[Recipe, ...]:
    terms = tuple(query.casefold().split())
    return tuple(
        recipe for recipe in recipes if all(term in recipe_search_text(recipe) for term in terms)
    )


def recipe_search_text(recipe: Recipe) -> str:
    command_text = " ".join(argument for command in recipe.commands for argument in command)
    return " ".join((recipe.title, recipe.description, *recipe.keywords, command_text)).casefold()


def recipe_by_id(recipes: Sequence[Recipe], recipe_id: str) -> Recipe | None:
    return next((recipe for recipe in recipes if recipe.recipe_id == recipe_id), None)


def plan_recipe_terminal(
    recipe: Recipe,
    python_executable: str = sys.executable,
) -> RecipeTerminalLaunch:
    return RecipeTerminalLaunch(
        (
            "/usr/bin/xfce4-terminal",
            "--window",
            "--hold",
            f"--title=Recipe — {recipe.title}",
            f"--working-directory={recipe.working_directory}",
            "--execute",
            python_executable,
            "-m",
            "whisper_app.recipe_runner",
            recipe.recipe_id,
        )
    )


def launch_recipe_terminal(
    recipe: Recipe,
    python_executable: str = sys.executable,
) -> subprocess.Popen[bytes]:
    if not recipe.working_directory.is_dir():
        raise RecipeCatalogError(f"Recipe directory does not exist: {recipe.working_directory}")
    plan = plan_recipe_terminal(recipe, python_executable)
    return subprocess.Popen(plan.argv, start_new_session=True)


__all__ = [
    "Recipe",
    "RecipeCatalogError",
    "RecipeTerminalLaunch",
    "launch_recipe_terminal",
    "load_recipe_catalog",
    "matching_recipes",
    "merge_recipe_catalogs",
    "plan_recipe_terminal",
    "read_recipe_catalog",
    "recipe_by_id",
    "recipe_catalog_paths",
    "recipe_from_mapping",
    "recipe_search_text",
]
