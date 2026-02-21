#!/bin/bash
# Setup isolated Python virtual environment and systemd service for Whisper GUI
#
# This script:
#   1. Creates a Python venv and installs dependencies
#   2. Generates a systemd user service from the template
#   3. Enables the service to start on login
#
# Usage:
#   cd /path/to/whisper
#   ./scripts/setup_venv_systemd.sh

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_DIR/venv"
SERVICE_NAME="whisper-gui"
SERVICE_TEMPLATE="$REPO_DIR/config/systemd/whisper-gui.service"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "Setting up Whisper GUI with isolated Python environment and systemd service..."
echo "  Project directory: $REPO_DIR"
echo ""

# Step 1: Create venv
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists at: $VENV_DIR"
else
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created"
fi

# Step 2: Install dependencies
echo ""
echo "Installing dependencies in virtual environment..."
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel > /dev/null 2>&1
"$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt" > /dev/null 2>&1
echo "Dependencies installed"

# Step 3: Generate and install systemd service
echo ""
echo "Setting up systemd user service..."

mkdir -p "$SYSTEMD_USER_DIR"

# Substitute project directory placeholder in the template
sed "s|WHISPER_PROJECT_DIR|$REPO_DIR|g" "$SERVICE_TEMPLATE" \
    > "$SYSTEMD_USER_DIR/$SERVICE_NAME.service"

echo "Service file installed to: $SYSTEMD_USER_DIR/$SERVICE_NAME.service"

# Step 4: Enable the service
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME.service"
echo "Service enabled"

echo ""
echo "Setup complete!"
echo ""
echo "Quick commands:"
echo "  Start now:      systemctl --user start $SERVICE_NAME"
echo "  Check status:   systemctl --user status $SERVICE_NAME"
echo "  View logs:      journalctl --user -u $SERVICE_NAME -f"
echo "  Stop:           systemctl --user stop $SERVICE_NAME"
echo "  Disable:        systemctl --user disable $SERVICE_NAME"
echo ""
echo "To set up a keyboard shortcut (e.g. Ctrl+Alt+Shift+R):"
echo "  Point the shortcut at: $REPO_DIR/scripts/whisper-recording-toggle toggle"
echo ""
echo "The service will start automatically on next login."
