#!/bin/bash
# Setup isolated Python virtual environment and systemd service for Whisper GUI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
GUI_SERVICE_NAME="whisper-gui"
GUI_SERVICE_FILE="$SCRIPT_DIR/whisper-gui.service"
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

# Step 3: Setup systemd service for the GUI
echo ""
echo "⚙️  Setting up systemd user services..."

# Create systemd user directory if it doesn't exist
mkdir -p "$SYSTEMD_USER_DIR"

# Copy the GUI service file
cp "$GUI_SERVICE_FILE" "$SYSTEMD_USER_DIR/$GUI_SERVICE_NAME.service"
echo "✅ GUI service file installed to: $SYSTEMD_USER_DIR/$GUI_SERVICE_NAME.service"

# Reload systemd and enable the GUI service
systemctl --user daemon-reload
systemctl --user enable "$GUI_SERVICE_NAME.service"
echo "✅ GUI service enabled"

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
echo "   GUI Service: $GUI_SERVICE_NAME"
echo "   Location: $SYSTEMD_USER_DIR/$GUI_SERVICE_NAME.service"
echo "   Status: Enabled (will start on next login)"
echo ""
echo "🎮 Quick Commands:"
echo ""
echo "   Start the service now:"
echo "   $ systemctl --user start $GUI_SERVICE_NAME"
echo ""
echo "   Check status:"
echo "   $ systemctl --user status $GUI_SERVICE_NAME"
echo ""
echo "   View GUI logs:"
echo "   $ journalctl --user -u $GUI_SERVICE_NAME -f"
echo ""
echo "   Stop the service:"
echo "   $ systemctl --user stop $GUI_SERVICE_NAME"
echo ""
echo "   Disable autostart:"
echo "   $ systemctl --user disable $GUI_SERVICE_NAME"
echo ""
echo "🔍 Verification:"
echo ""
echo "   Check venv works:"
echo "   $ source $VENV_DIR/bin/activate"
echo "   $ python3 --version"
echo "   $ deactivate"
echo ""
echo "   Check the service is enabled:"
echo "   $ systemctl --user is-enabled $GUI_SERVICE_NAME"
echo ""
echo "✨ Whisper will start automatically on next login!"
echo "   The built-in HotkeyBackend will monitor CTRL+ALT+SHIFT+R to toggle recording!"
echo ""
