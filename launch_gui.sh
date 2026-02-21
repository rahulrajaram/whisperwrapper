#!/bin/bash
# Launcher script for Whisper GUI

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python3."
    exit 1
fi

# Check if PyQt6 is installed
if ! python3 -c "import PyQt6" 2>/dev/null; then
    echo "⚠️  PyQt6 not installed."
    echo "Installing PyQt6..."
    pip install PyQt6
fi

# Navigate to script directory and run GUI
cd "$SCRIPT_DIR"
exec python3 whisper_gui.py "$@"
