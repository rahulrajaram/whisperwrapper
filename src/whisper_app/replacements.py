"""Manage the Whisper replacements file (~/.whisper/replacements.txt)."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

REPLACEMENTS_PATH = Path.home() / ".whisper" / "replacements.txt"


def _read_mappings() -> List[Tuple[str, str]]:
    if not REPLACEMENTS_PATH.exists():
        return []
    mappings = []
    for line in REPLACEMENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if " -> " not in line:
            continue
        source, target = line.split(" -> ", 1)
        source, target = source.strip(), target.strip()
        if source:
            mappings.append((source, target))
    return mappings


def _write_mappings(mappings: List[Tuple[str, str]]) -> None:
    REPLACEMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    unique: List[Tuple[str, str]] = []
    for source, target in mappings:
        key = source.lower()
        if key not in seen:
            seen.add(key)
            unique.append((source, target))
    content = "\n".join(f"{s} -> {t}" for s, t in unique) + "\n" if unique else ""
    REPLACEMENTS_PATH.write_text(content, encoding="utf-8")


def load_replacements() -> Dict[str, str]:
    """Parse replacements file into {source: target} dict."""
    return {source: target for source, target in _read_mappings()}


def apply_replacements(text: str, replacements: Dict[str, str]) -> str:
    """Apply word-boundary replacements, case-insensitive, preserving original case pattern."""
    if not replacements:
        return text
    for source, target in replacements.items():
        pattern = re.compile(r"\b" + re.escape(source) + r"\b", re.IGNORECASE)
        text = pattern.sub(_make_case_preserver(target), text)
    return text


def _make_case_preserver(target: str):
    """Return a replacement function that preserves the matched text's case pattern."""
    def replacer(match: re.Match) -> str:
        matched = match.group(0)
        if matched.isupper():
            return target.upper()
        if matched.islower():
            return target.lower()
        if matched[0].isupper() and matched[1:].islower():
            return target[0].upper() + target[1:].lower() if len(target) > 1 else target.upper()
        return target
    return replacer


def cmd_add(source: str, target: str) -> None:
    mappings = _read_mappings()
    existing_keys = {s.lower() for s, _ in mappings}
    if source.lower() in existing_keys:
        mappings = [(s, t) if s.lower() != source.lower() else (source, target) for s, t in mappings]
        print(f"Updated: {source} -> {target}")
    else:
        mappings.append((source, target))
        print(f"Added: {source} -> {target}")
    _write_mappings(mappings)
    print(f"Total: {len(mappings)}")


def cmd_rm(source: str) -> None:
    mappings = _read_mappings()
    remaining = [(s, t) for s, t in mappings if s.lower() != source.lower()]
    removed = len(mappings) - len(remaining)
    _write_mappings(remaining)
    if removed:
        print(f"Removed: {source}")
    else:
        print(f"Not found: {source}")
    print(f"Total: {len(remaining)}")


def cmd_list() -> None:
    mappings = _read_mappings()
    if not mappings:
        print("(empty)")
        return
    for source, target in mappings:
        print(f"{source} -> {target}")
    print(f"\n{len(mappings)} replacement(s)")


def cmd_clear() -> None:
    _write_mappings([])
    print("Replacements cleared")


def run_replace(args: List[str]) -> None:
    """Dispatch replace subcommands."""
    usage = (
        "Usage: whisperwrapper replace <command> [args]\n"
        "\n"
        "Commands:\n"
        "  add SOURCE TARGET     Add a word replacement mapping\n"
        "  rm SOURCE             Remove a replacement\n"
        "  list                  Show current replacements\n"
        "  clear                 Remove all replacements"
    )

    if not args:
        print(usage)
        sys.exit(1)

    action = args[0]

    if action == "add":
        if len(args) < 3:
            print("Usage: whisperwrapper replace add SOURCE TARGET", file=sys.stderr)
            sys.exit(1)
        cmd_add(args[1], args[2])
    elif action == "rm":
        if len(args) < 2:
            print("Usage: whisperwrapper replace rm SOURCE", file=sys.stderr)
            sys.exit(1)
        cmd_rm(args[1])
    elif action == "list":
        cmd_list()
    elif action == "clear":
        cmd_clear()
    else:
        print(f"Unknown replace command: {action}", file=sys.stderr)
        print(usage)
        sys.exit(1)
