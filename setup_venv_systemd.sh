#!/bin/bash
# Setup isolated Python virtual environment and systemd service for Whisper GUI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
SERVICE_NAME="whisper-gui"
SERVICE_FILE="$SCRIPT_DIR/whisper-gui.service"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "🚀 Setting up Whisper GUI with isolated Python environment and systemd service..."
echo ""

# Step 1: Check if venv already exists
if [ -d "$VENV_DIR" ]; then
    echo "✅ Virtual environment already exists at: $VENV_DIR"
else
    echo "📦 Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✅ Virtual environment created"
fi

# Step 2: Activate venv and install dependencies
echo ""
echo "📚 Installing dependencies in virtual environment..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
pip install -r "$SCRIPT_DIR/requirements.txt" > /dev/null 2>&1
deactivate
echo "✅ Dependencies installed"

# Step 3: Setup systemd service
echo ""
echo "⚙️  Setting up systemd user service..."

# Create systemd user directory if it doesn't exist
mkdir -p "$SYSTEMD_USER_DIR"

# Copy the service file
cp "$SERVICE_FILE" "$SYSTEMD_USER_DIR/$SERVICE_NAME.service"
echo "✅ Service file installed to: $SYSTEMD_USER_DIR/$SERVICE_NAME.service"

# Enable the service
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME.service"
echo "✅ Service enabled"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🎉 Setup Complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📍 Virtual Environment:"
echo "   Location: $VENV_DIR"
echo "   Python: $VENV_DIR/bin/python3"
echo ""
echo "📍 Systemd Service:"
echo "   Service: $SERVICE_NAME"
echo "   Location: $SYSTEMD_USER_DIR/$SERVICE_NAME.service"
echo "   Status: Enabled (will start on next login)"
echo ""
echo "🎮 Quick Commands:"
echo ""
echo "   Start now (without logging out):"
echo "   $ systemctl --user start $SERVICE_NAME"
echo ""
echo "   Check status:"
echo "   $ systemctl --user status $SERVICE_NAME"
echo ""
echo "   View logs:"
echo "   $ journalctl --user -u $SERVICE_NAME -f"
echo ""
echo "   Stop service:"
echo "   $ systemctl --user stop $SERVICE_NAME"
echo ""
echo "   Disable autostart:"
echo "   $ systemctl --user disable $SERVICE_NAME"
echo ""
echo "🔍 Verification:"
echo ""
echo "   Check venv works:"
echo "   $ source $VENV_DIR/bin/activate"
echo "   $ python3 --version"
echo "   $ deactivate"
echo ""
echo "   Check service status:"
echo "   $ systemctl --user status $SERVICE_NAME"
echo ""
echo "✨ Whisper will start automatically on next login!"
echo ""
