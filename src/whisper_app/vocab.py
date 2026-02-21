"""Manage the Whisper vocabulary file (~/.whisper/vocabulary.txt)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Set

VOCAB_PATH = Path.home() / ".whisper" / "vocabulary.txt"


def _read_terms() -> List[str]:
    if not VOCAB_PATH.exists():
        return []
    lines = VOCAB_PATH.read_text(encoding="utf-8").splitlines()
    return [t.strip() for t in lines if t.strip()]


def _write_terms(terms: List[str]) -> None:
    VOCAB_PATH.parent.mkdir(parents=True, exist_ok=True)
    seen: Set[str] = set()
    unique: List[str] = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    VOCAB_PATH.write_text("\n".join(unique) + "\n" if unique else "", encoding="utf-8")


def cmd_add(new_terms: List[str]) -> None:
    existing = _read_terms()
    existing_set = set(existing)
    added = []
    for t in new_terms:
        if t not in existing_set:
            existing.append(t)
            existing_set.add(t)
            added.append(t)
    _write_terms(existing)
    if added:
        print(f"Added {len(added)} term(s): {', '.join(added)}")
    else:
        print("All terms already present")
    print(f"Total: {len(existing)}")


def cmd_rm(remove_terms: List[str]) -> None:
    existing = _read_terms()
    remove_set = set(remove_terms)
    remaining = [t for t in existing if t not in remove_set]
    removed = len(existing) - len(remaining)
    _write_terms(remaining)
    print(f"Removed {removed} term(s). Total: {len(remaining)}")


def cmd_list() -> None:
    terms = _read_terms()
    if not terms:
        print("(empty)")
        return
    for t in terms:
        print(t)
    print(f"\n{len(terms)} term(s)")


def cmd_import(filepath: str) -> None:
    src = Path(filepath)
    if not src.exists():
        print(f"File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    new_terms = [t.strip() for t in src.read_text(encoding="utf-8").splitlines() if t.strip()]
    if not new_terms:
        print("No terms found in file")
        return
    cmd_add(new_terms)


def cmd_clear() -> None:
    _write_terms([])
    print("Vocabulary cleared")


def run_vocab(args: List[str]) -> None:
    """Dispatch vocab subcommands."""
    usage = (
        "Usage: whisperwrapper vocab <command> [args]\n"
        "\n"
        "Commands:\n"
        "  add TERM [TERM ...]   Add terms (deduplicates automatically)\n"
        "  rm TERM [TERM ...]    Remove terms\n"
        "  list                  Show current vocabulary\n"
        "  import FILE           Import terms from a file (one per line)\n"
        "  clear                 Remove all terms"
    )

    if not args:
        print(usage)
        sys.exit(1)

    action = args[0]

    if action == "add":
        if len(args) < 2:
            print("Usage: whisperwrapper vocab add TERM [TERM ...]", file=sys.stderr)
            sys.exit(1)
        cmd_add(args[1:])
    elif action == "rm":
        if len(args) < 2:
            print("Usage: whisperwrapper vocab rm TERM [TERM ...]", file=sys.stderr)
            sys.exit(1)
        cmd_rm(args[1:])
    elif action == "list":
        cmd_list()
    elif action == "import":
        if len(args) < 2:
            print("Usage: whisperwrapper vocab import FILE", file=sys.stderr)
            sys.exit(1)
        cmd_import(args[1])
    elif action == "clear":
        cmd_clear()
    else:
        print(f"Unknown vocab command: {action}", file=sys.stderr)
        print(usage)
        sys.exit(1)
