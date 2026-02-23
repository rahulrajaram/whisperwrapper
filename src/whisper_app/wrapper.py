"""whisperwrapper — unified entry point for Whisper GUI, CLI, and vocabulary management."""

from __future__ import annotations

import sys


USAGE = """\
Usage: whisperwrapper <command> [args]

Commands:
  gui                   Launch the PyQt6 desktop GUI
  cli                   Run the headless CLI transcriber
  vocab <subcommand>    Manage vocabulary (~/.whisper/vocabulary.txt)
  replace <subcommand>  Manage word replacements (~/.whisper/replacements.txt)

Run 'whisperwrapper vocab' or 'whisperwrapper replace' for subcommands.\
"""


def main() -> None:
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)

    command = sys.argv[1]

    if command == "gui":
        from .gui import main as gui_main
        gui_main()
    elif command == "cli":
        from .cli import WhisperCLI
        # Strip 'cli' from argv so argparse in WhisperCLI works
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        cli = WhisperCLI(headless=True)
        cli.run_headless()
    elif command == "vocab":
        from .vocab import run_vocab
        run_vocab(sys.argv[2:])
    elif command == "replace":
        from .replacements import run_replace
        run_replace(sys.argv[2:])
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
