#!/bin/bash
# Setup script for Whisper Hotkey Daemon
# Installs dependencies and configures permissions

set -e

echo "🚀 Setting up Whisper Hotkey Daemon..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Wayland/X11 Linux with Debian
if ! grep -q "ID=debian\|ID_LIKE=.*debian" /etc/os-release 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Warning: This script is optimized for Debian-based systems${NC}"
fi

echo ""
echo "📦 Step 1: Installing dependencies..."

# Install python3-evdev
if ! dpkg -l | grep -q python3-evdev; then
    echo "  Installing python3-evdev..."
    sudo apt-get update
    sudo apt-get install -y python3-evdev
    echo -e "  ${GREEN}✅ Installed python3-evdev${NC}"
else
    echo -e "  ${GREEN}✅ python3-evdev already installed${NC}"
fi

# Install clipboard tools
CLIPBOARD_INSTALLED=false

if command -v wl-copy &> /dev/null; then
    echo -e "  ${GREEN}✅ wl-copy (Wayland clipboard) found${NC}"
    CLIPBOARD_INSTALLED=true
elif command -v xclip &> /dev/null; then
    echo -e "  ${GREEN}✅ xclip (X11 clipboard) found${NC}"
    CLIPBOARD_INSTALLED=true
elif command -v xsel &> /dev/null; then
    echo -e "  ${GREEN}✅ xsel (X11 clipboard) found${NC}"
    CLIPBOARD_INSTALLED=true
fi

if [ "$CLIPBOARD_INSTALLED" = false ]; then
    echo "  Installing wl-clipboard (Wayland) and xclip (X11 fallback)..."
    sudo apt-get install -y wl-clipboard xclip
    echo -e "  ${GREEN}✅ Clipboard tools installed${NC}"
fi

echo ""
echo "🔐 Step 2: Setting up permissions..."

# Add user to input group
if id -nG "$USER" | grep -qw "input"; then
    echo -e "  ${GREEN}✅ User already in 'input' group${NC}"
else
    echo "  Adding user to 'input' group..."
    sudo usermod -a -G input "$USER"
    echo -e "  ${YELLOW}⚠️  You must log out and log back in for group changes to take effect${NC}"
fi

echo ""
echo "📋 Step 3: Creating udev rule..."

# Create udev rule for input device access
UDEV_RULE="/etc/udev/rules.d/99-input-whisper.rules"
UDEV_CONTENT='KERNEL=="event*", SUBSYSTEM=="input", MODE="0660", GROUP="input"'

if sudo test -f "$UDEV_RULE"; then
    if sudo grep -q "input-whisper" "$UDEV_RULE"; then
        echo -e "  ${GREEN}✅ udev rule already exists${NC}"
    else
        echo "  Updating udev rule..."
        echo "$UDEV_CONTENT" | sudo tee "$UDEV_RULE" > /dev/null
        sudo udevadm control --reload-rules
        sudo udevadm trigger
        echo -e "  ${GREEN}✅ udev rule updated${NC}"
    fi
else
    echo "  Creating udev rule..."
    echo "$UDEV_CONTENT" | sudo tee "$UDEV_RULE" > /dev/null
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    echo -e "  ${GREEN}✅ udev rule created${NC}"
fi

echo ""
echo "⚙️  Step 4: Making scripts executable..."

chmod +x "$(dirname "$0")/whisper_hotkey_daemon.py"
chmod +x "$(dirname "$0")/whisper_hotkey_recorder.py"
echo -e "  ${GREEN}✅ Scripts made executable${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Setup complete!${NC}"
echo "=========================================="
echo ""
echo "📖 Next steps:"
echo ""
echo "1. Log out and log back in for group changes to take effect"
echo "   (or run: newgrp input)"
echo ""
echo "2. Test the hotkey daemon:"
echo "   ./$(dirname "$0")/whisper_hotkey_daemon.py --debug"
echo ""
echo "3. Press CTRL+SHIFT+R to start recording"
echo "   Press RETURN or ESC to stop recording and save to clipboard"
echo ""
echo "🔧 To run as a daemon on startup:"
echo "   Check the README.md for systemd service setup instructions"
echo ""
