#!/bin/bash
# Setup isolated Python virtual environment and systemd service for Whisper GUI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
GUI_SERVICE_NAME="whisper-gui"
GUI_SERVICE_FILE="$SCRIPT_DIR/whisper-gui.service"
DAEMON_SERVICE_NAME="whisper-hotkey-daemon"
DAEMON_SERVICE_FILE="$SCRIPT_DIR/whisper-hotkey-daemon.service"
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

# Step 3: Setup systemd services (GUI and hotkey daemon)
echo ""
echo "⚙️  Setting up systemd user services..."

# Create systemd user directory if it doesn't exist
mkdir -p "$SYSTEMD_USER_DIR"

# Copy the GUI service file
cp "$GUI_SERVICE_FILE" "$SYSTEMD_USER_DIR/$GUI_SERVICE_NAME.service"
echo "✅ GUI service file installed to: $SYSTEMD_USER_DIR/$GUI_SERVICE_NAME.service"

# Copy the hotkey daemon service file
cp "$DAEMON_SERVICE_FILE" "$SYSTEMD_USER_DIR/$DAEMON_SERVICE_NAME.service"
echo "✅ Hotkey daemon service file installed to: $SYSTEMD_USER_DIR/$DAEMON_SERVICE_NAME.service"

# Reload systemd and enable both services
systemctl --user daemon-reload
systemctl --user enable "$GUI_SERVICE_NAME.service"
systemctl --user enable "$DAEMON_SERVICE_NAME.service"
echo "✅ Both services enabled"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🎉 Setup Complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📍 Virtual Environment:"
echo "   Location: $VENV_DIR"
echo "   Python: $VENV_DIR/bin/python3"
echo ""
echo "📍 Systemd Services:"
echo "   GUI Service: $GUI_SERVICE_NAME"
echo "   GUI Location: $SYSTEMD_USER_DIR/$GUI_SERVICE_NAME.service"
echo "   Status: Enabled (will start on next login)"
echo ""
echo "   Hotkey Daemon: $DAEMON_SERVICE_NAME"
echo "   Daemon Location: $SYSTEMD_USER_DIR/$DAEMON_SERVICE_NAME.service"
echo "   Status: Enabled (will start on next login)"
echo ""
echo "🎮 Quick Commands:"
echo ""
echo "   Start both services now:"
echo "   $ systemctl --user start $GUI_SERVICE_NAME $DAEMON_SERVICE_NAME"
echo ""
echo "   Check status of both:"
echo "   $ systemctl --user status $GUI_SERVICE_NAME"
echo "   $ systemctl --user status $DAEMON_SERVICE_NAME"
echo ""
echo "   View GUI logs:"
echo "   $ journalctl --user -u $GUI_SERVICE_NAME -f"
echo ""
echo "   View hotkey daemon logs:"
echo "   $ journalctl --user -u $DAEMON_SERVICE_NAME -f"
echo ""
echo "   Stop both services:"
echo "   $ systemctl --user stop $GUI_SERVICE_NAME $DAEMON_SERVICE_NAME"
echo ""
echo "   Disable autostart:"
echo "   $ systemctl --user disable $GUI_SERVICE_NAME $DAEMON_SERVICE_NAME"
echo ""
echo "🔍 Verification:"
echo ""
echo "   Check venv works:"
echo "   $ source $VENV_DIR/bin/activate"
echo "   $ python3 --version"
echo "   $ deactivate"
echo ""
echo "   Check both services are enabled:"
echo "   $ systemctl --user is-enabled $GUI_SERVICE_NAME"
echo "   $ systemctl --user is-enabled $DAEMON_SERVICE_NAME"
echo ""
echo "⚙️  Additional Setup:"
echo "   The hotkey daemon requires xbindkeys for global hotkey support."
echo "   Install with: sudo apt install xbindkeys"
echo ""
echo "✨ Whisper will start automatically on next login!"
echo "   The hotkey daemon will monitor CTRL+ALT+SHIFT+R to toggle recording!"
echo ""
