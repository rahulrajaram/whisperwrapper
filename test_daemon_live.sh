#!/bin/bash
# Test script to verify daemon is receiving key events

echo "🧪 Live Daemon Test"
echo "========================================"
echo ""
echo "This script will:"
echo "1. Start the daemon in background"
echo "2. Wait for you to press CTRL+ALT+R in a different window"
echo "3. Show if the daemon is receiving the key press"
echo ""
echo "INSTRUCTIONS:"
echo "1. This script will start the daemon"
echo "2. Open a DIFFERENT window/application (browser, text editor, etc)"
echo "3. In that DIFFERENT window, press CTRL+ALT+R"
echo "4. This script will show if the daemon detected it"
echo ""
read -p "Press ENTER to start..."

echo ""
echo "Starting daemon in background..."
sudo ./whisper_hotkey_daemon.py --debug > /tmp/daemon_output.log 2>&1 &
DAEMON_PID=$!

echo "Daemon PID: $DAEMON_PID"
echo ""
echo "Now open a different application and press CTRL+ALT+R..."
echo "(Waiting 15 seconds...)"
echo ""

# Wait and show output
sleep 3
echo "=== Daemon output so far ==="
tail -20 /tmp/daemon_output.log
echo ""

sleep 12
echo ""
echo "=== Final daemon output ==="
tail -30 /tmp/daemon_output.log

echo ""
echo "Stopping daemon..."
kill $DAEMON_PID 2>/dev/null

echo ""
echo "Check:"
if grep -q "CTRL\|KEY_R\|detected" /tmp/daemon_output.log; then
    echo "✅ Daemon received key events!"
else
    echo "❌ No key events received by daemon"
    echo ""
    echo "Possible reasons:"
    echo "1. You didn't press CTRL+ALT+R in a different window"
    echo "2. The hotkey might not be detected as CTRL+ALT+R"
    echo "3. The device isn't receiving the key events"
fi

echo ""
echo "Full log saved to: /tmp/daemon_output.log"
