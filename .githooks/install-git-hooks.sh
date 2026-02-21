#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
if [ -z "$repo_root" ]; then
  echo "Not inside a git repository."
  exit 1
fi

hooks_dir="$repo_root/.githooks"
if [ ! -d "$hooks_dir" ]; then
  echo "Hooks directory not found: $hooks_dir" >&2
  exit 1
fi

git config core.hooksPath "$hooks_dir"
chmod +x "$hooks_dir/pre-commit" "$hooks_dir/commit-msg"
echo "Git hooks set to: $hooks_dir"
echo " - pre-commit: $hooks_dir/pre-commit"
echo " - commit-msg: $hooks_dir/commit-msg"
