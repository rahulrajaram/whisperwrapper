#!/bin/bash
# Install whisperwrapper and supporting scripts into ~/.local/bin
#
# Usage:
#   ./install.sh
#
# This creates symlinks in ~/.local/bin pointing back to this repo,
# so updates to the repo are picked up immediately.

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$BIN_DIR"

# Symlink whisperwrapper
ln -sf "$REPO_DIR/bin/whisperwrapper" "$BIN_DIR/whisperwrapper"
echo "Installed: $BIN_DIR/whisperwrapper -> $REPO_DIR/bin/whisperwrapper"

# Symlink whisper-recording-toggle
ln -sf "$REPO_DIR/scripts/whisper-recording-toggle" "$BIN_DIR/whisper-recording-toggle"
echo "Installed: $BIN_DIR/whisper-recording-toggle -> $REPO_DIR/scripts/whisper-recording-toggle"

echo ""
echo "Done. Make sure ~/.local/bin is on your PATH."
echo ""
echo "Usage:"
echo "  whisperwrapper gui                  # Launch GUI"
echo "  whisperwrapper vocab add TERM       # Add vocabulary terms"
echo "  whisperwrapper vocab list           # List vocabulary"
echo "  whisper-recording-toggle toggle     # Toggle recording (for shortcuts)"
