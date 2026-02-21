#!/bin/bash
# Setup Whisper GUI autostart on system launch

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_FILE="$SCRIPT_DIR/whisper-gui-autostart.desktop"
AUTOSTART_DIR="$HOME/.config/autostart"

echo "🚀 Setting up Whisper GUI autostart..."

# Create autostart directory if it doesn't exist
mkdir -p "$AUTOSTART_DIR"

# Copy the desktop file to autostart directory
cp "$DESKTOP_FILE" "$AUTOSTART_DIR/whisper-gui-autostart.desktop"

echo "✅ Autostart configured!"
echo ""
echo "📍 Desktop file location: $AUTOSTART_DIR/whisper-gui-autostart.desktop"
echo ""
echo "Whisper will now start automatically when you log in to KDE."
echo ""
echo "To disable autostart, run:"
echo "  rm $AUTOSTART_DIR/whisper-gui-autostart.desktop"
echo ""
echo "Or use KDE System Settings > Startup and Shutdown > Autostart"
