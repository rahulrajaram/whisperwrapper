#!/bin/bash
# Start the Whisper Hotkey Daemon
# Run this from your actual desktop terminal (not the IDE terminal)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Whisper Hotkey Daemon..."
echo ""
echo "Make sure you're running this from your actual desktop terminal!"
echo "If running from an IDE terminal, the daemon won't receive keyboard events."
echo ""
echo "Hotkeys:"
echo "  CTRL+ALT+R - Start/stop recording"
echo "  RETURN or ESC - Stop recording and save to clipboard"
echo ""
echo "Press CTRL+C to stop the daemon"
echo ""

# Run the daemon
python3 whisper_hotkey_daemon.py "$@"
