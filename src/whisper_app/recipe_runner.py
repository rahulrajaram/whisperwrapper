"""Execute one declarative recipe inside its dedicated terminal."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence

from .recipes import Recipe, RecipeCatalogError, load_recipe_catalog, recipe_by_id


def expanded_command(command: Sequence[str]) -> tuple[str, ...]:
    return tuple(os.path.expandvars(os.path.expanduser(argument)) for argument in command)


def run_recipe(recipe: Recipe) -> int:
    for command in recipe.commands:
        expanded = expanded_command(command)
        print(f"\n▶ {' '.join(expanded)}\n", flush=True)
        try:
            result = subprocess.run(expanded, cwd=recipe.working_directory, check=False)
        except OSError as error:
            print(f"Could not execute recipe command: {error}", file=sys.stderr)
            return 127
        if result.returncode != 0:
            print(f"\nRecipe stopped with status {result.returncode}.", file=sys.stderr)
            return result.returncode
    print("\n✓ Recipe completed.", flush=True)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one Whisper launcher recipe")
    parser.add_argument("recipe_id")
    args = parser.parse_args(argv)
    try:
        recipes = load_recipe_catalog()
    except RecipeCatalogError as error:
        print(error, file=sys.stderr)
        return 2
    recipe = recipe_by_id(recipes, args.recipe_id)
    if recipe is None:
        print(f"Unknown recipe: {args.recipe_id}", file=sys.stderr)
        return 2
    return run_recipe(recipe)


if __name__ == "__main__":  # pragma: no cover - module execution boundary
    raise SystemExit(main())
