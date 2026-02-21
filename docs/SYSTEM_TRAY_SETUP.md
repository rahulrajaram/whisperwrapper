# Whisper Voice Recording - System Tray & Autostart Setup

## Overview

Whisper now integrates with your KDE system tray (the panel at the bottom showing time, WiFi, Bluetooth, etc.). You can access it like other system apps (Zoom, etc.) and optionally have it start automatically when you log in.

## Features

### System Tray Integration
- **Tray Icon**: Green microphone icon appears in KDE panel
- **Status Display**: Shows "Ready" or "Recording..." status
- **Quick Access**: Right-click menu for recording controls
- **Minimize to Tray**: Click the window close button to hide the window (keeps running in tray)
- **Restore Window**: Double-click tray icon or select "Show/Hide" to bring window back

### Right-Click Tray Menu
```
Show/Hide          - Toggle main window visibility
─────────────────────
🎤 Ready           - Current recording status (display only)
─────────────────────
▶ Start Recording  - Begin recording immediately
⏹ Stop Recording   - Stop recording and process
─────────────────────
Exit               - Close the application
```

## System Tray Usage

### Access from KDE Panel
1. Look for the **green microphone icon** in your system tray (bottom right area)
2. **Right-click** on it to see the menu
3. **Double-click** to show/hide the main window

### Recording from Tray
- Click **▶ Start Recording** to begin
- Click **⏹ Stop Recording** to finish and transcribe
- Status updates in real-time

### Minimize & Hide
- Click the **X** button on the window to hide it (doesn't close the app)
- The app stays running in the tray
- Double-click the tray icon to restore the window

## Autostart Setup

### Quick Setup (Recommended)
```bash
cd ~/Documents/whisper
./setup_autostart.sh
```

This will:
1. Create the autostart configuration
2. Place it in `~/.config/autostart/`
3. Enable automatic startup on next login

### Manual Setup
If you prefer to do it manually:

```bash
# Copy the desktop file to autostart
cp ~/Documents/whisper/whisper-gui-autostart.desktop ~/.config/autostart/
```

### Using KDE Settings
1. Open **KDE System Settings**
2. Go to **Startup and Shutdown** > **Autostart**
3. Click the **+ Add Program...** button
4. Select `/home/rahul/Documents/whisper/launch_gui.sh`
5. Click **OK**

## Verification

### Check if Autostart is Enabled
```bash
# File should exist if autostart is set up
ls ~/.config/autostart/whisper-gui-autostart.desktop
```

### Check if It Starts on Login
1. Log out of your KDE session
2. Log back in
3. The Whisper tray icon should appear in the panel within a few seconds

## Disable Autostart

### Method 1: Remove the File
```bash
rm ~/.config/autostart/whisper-gui-autostart.desktop
```

### Method 2: Using KDE Settings
1. Open **KDE System Settings**
2. Go to **Startup and Shutdown** > **Autostart**
3. Find "Whisper Voice Recording" in the list
4. Click the **-** (remove) button

## How It Works

### System Tray Technical Details
- Uses `QSystemTrayIcon` from PyQt6
- Draws a custom microphone icon using `QPainter`
- Right-click menu is a standard `QMenu` connected to application functions
- Window can be hidden/shown while maintaining background recording capability

### Autostart Technical Details
- `.desktop` file format used by KDE/GNOME/Freedesktop
- Located in `~/.config/autostart/` directory
- `X-KDE-AutostartPhase=2` ensures it starts after KDE initialization
- `StartupNotify=false` for silent background startup
- App starts in system tray mode by default

## Starting Manually

If autostart is not set up, you can still run manually:

```bash
# From terminal
cd ~/Documents/whisper
./whisper_gui.py

# Or from launcher
~/Documents/whisper/launch_gui.sh
```

## Troubleshooting

### Tray Icon Not Showing
1. Check that you're using a modern KDE version (5.20+)
2. Restart KDE: `killall plasmashell && kstart plasmashell`
3. Try running directly: `python3 ~/Documents/whisper/whisper_gui.py`

### Autostart Not Working
1. Verify file exists: `ls ~/.config/autostart/whisper-gui-autostart.desktop`
2. Check file permissions: `cat ~/.config/autostart/whisper-gui-autostart.desktop`
3. Check KDE System Settings > Startup and Shutdown > Autostart
4. Look for any error messages in: `~/.local/share/kdedefaults/plasmashell/crash.log`

### Application Crashes on Autostart
1. Run manually to check for errors: `python3 ~/Documents/whisper/whisper_gui.py 2>&1 | head -20`
2. Check system logs: `journalctl -n 20`
3. Make sure all dependencies are installed: `pip install -r ~/Documents/whisper/requirements.txt`

## Keyboard Shortcuts (Optional)

You can set up global keyboard shortcuts through KDE Settings:
1. Open **KDE System Settings**
2. Go to **Shortcuts** > **Global Shortcuts**
3. Search for "Whisper"
4. Set your preferred hotkey (e.g., Ctrl+Alt+R)

## Tips & Best Practices

### Power Users
- Keep Whisper in tray at all times
- Use minimize button (X) to close window, not exit
- Access from tray menu for quick recordings
- Check status at a glance in the tray

### For Maximum Privacy
- Window can be minimized to tray during use
- No one can see what you're recording if window is hidden
- Status only shows "Ready" or "Recording..." (no transcription details)

### For Better Performance
- Closing the window (hiding in tray) saves memory
- The app uses minimal CPU when idle
- Recording and transcription only happen when you trigger it

## File Locations

```
~/Documents/whisper/
├── whisper_gui.py              ← Main application
├── whisper-gui.desktop         ← Application launcher
├── whisper-gui-autostart.desktop ← Autostart configuration
└── setup_autostart.sh          ← Setup script

~/.config/autostart/
└── whisper-gui-autostart.desktop ← Installed autostart file

~/.whisper/
└── gui_history.json            ← Transcription history
```

## Support

For issues or questions:
1. Check this guide first
2. Try running manually to see error messages
3. Check the main README.md and GETTING_STARTED_GUI.md files
4. Review whisper_gui.py comments and code

Enjoy your voice recording setup! 🎤
