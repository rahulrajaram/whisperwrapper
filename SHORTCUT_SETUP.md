# Whisper Recording Control via KDE Shortcuts

## Overview

The Whisper GUI communicates via **Unix signals** for recording control. This approach works reliably on both X11 and Wayland, avoiding the global hotkey limitations of Wayland.

## How It Works

1. **Whisper GUI** stores its process ID in `~/.whisper/app.lock`
2. **whisper-recording-toggle** script reads the PID and sends signals to the GUI:
   - `toggle` → SIGUSR1 (toggle recording on/off)
   - `start` → SIGUSR2 (start recording)
   - `stop` → SIGALRM (stop recording)
3. **KDE System Settings** can execute these commands via custom keyboard shortcuts

## Setting Up KDE Shortcuts

### Method 1: Using KDE System Settings (GUI)

1. **Open KDE Settings:**
   ```bash
   systemsettings6 &
   ```
   Or: Press `Alt+F2` → search "Settings" → click it

2. **Navigate to:**
   - Sidebar: **Shortcuts**
   - Then click **Custom Shortcuts**

3. **Create a new shortcut group (if needed):**
   - Click **Edit** → **New Group**
   - Name it: `Whisper`
   - Click **Save**

4. **Add shortcut for Toggle Recording:**
   - Select the `Whisper` group
   - Click **New** → **New Command/URL**
   - **Name:** `Toggle Recording`
   - **Trigger:** Choose your key combination
     - Recommended: `Ctrl+Alt+Shift+R` (if not already used)
     - Or: `Super+R` (if Meta key is free)
   - **Action:** `/home/rahul/.local/bin/whisper-recording-toggle toggle`
   - Click **Apply**

5. **(Optional) Add shortcuts for Start/Stop:**
   - Create another shortcut:
     - **Name:** `Start Recording`
     - **Trigger:** `Ctrl+Alt+Shift+S` (or your choice)
     - **Action:** `/home/rahul/.local/bin/whisper-recording-toggle start`
   - Create another shortcut:
     - **Name:** `Stop Recording`
     - **Trigger:** `Ctrl+Alt+Shift+E` (or your choice)
     - **Action:** `/home/rahul/.local/bin/whisper-recording-toggle stop`

6. **Click Apply and Close Settings**

### Method 2: Manual Configuration (Text-Based)

If you prefer editing configuration files directly:

**File location:** `~/.config/khotkeysrc`

**Add this section:**
```ini
[Whisper]
Enabled=true

[Whisper][Toggle Recording]
Type=COMMAND_URL
Exec=/home/rahul/.local/bin/whisper-recording-toggle toggle
Name=Toggle Recording
Shortcut=Ctrl+Alt+Shift+R

[Whisper][Start Recording]
Type=COMMAND_URL
Exec=/home/rahul/.local/bin/whisper-recording-toggle start
Name=Start Recording
Shortcut=Ctrl+Alt+Shift+S

[Whisper][Stop Recording]
Type=COMMAND_URL
Exec=/home/rahul/.local/bin/whisper-recording-toggle stop
Name=Stop Recording
Shortcut=Ctrl+Alt+Shift+E
```

Then reload KDE shortcuts:
```bash
qdbus org.kde.KGlobalShortcuts /component/khotkeys reloadConfiguration
```

## Testing the Shortcuts

1. **Start the Whisper GUI:**
   ```bash
   systemctl --user start whisper-gui
   ```

2. **Test toggle signal:**
   ```bash
   whisper-recording-toggle toggle
   ```

   You should see:
   - In GUI logs: `🔔 Received toggle signal (SIGUSR1)`
   - In system status bar or GUI: Recording status changes

3. **Verify script found the GUI:**
   ```bash
   whisper-recording-toggle status
   ```

   Should output:
   ```
   Found Whisper GUI (PID: XXXXX)
   GUI is running (PID: XXXXX)
   ```

## Troubleshooting

### "Whisper GUI is not running" error
- Make sure the GUI is started: `systemctl --user start whisper-gui`
- Check if lock file exists: `cat ~/.whisper/app.lock`

### Shortcut not triggering
1. **Verify shortcut is enabled:**
   - Open KDE Settings → Shortcuts
   - Make sure "Whisper" group is listed and enabled

2. **Check for key conflicts:**
   - The same key might be bound to another application
   - Open Settings → Shortcuts → "All Applications"
   - Search for your chosen key combination to see if it's already used

3. **Reload KDE configuration:**
   ```bash
   qdbus org.kde.KGlobalShortcuts /component/khotkeys reloadConfiguration
   ```

4. **Check if the script is executable:**
   ```bash
   ls -l ~/.local/bin/whisper-recording-toggle
   # Should show: -rwxr-xr-x
   ```

### GUI doesn't respond to signals
1. **Check GUI is actually running:**
   ```bash
   ps aux | grep whisper_app | grep -v grep
   ```

2. **Check GUI logs:**
   ```bash
   journalctl --user -u whisper-gui -n 30
   ```
   Should show:
   ```
   ✅ Signal handlers registered (SIGUSR1/SIGUSR2/SIGALRM)
   ```

3. **Test signal manually:**
   ```bash
   kill -USR1 $(cat ~/.whisper/app.lock)
   ```
   Should toggle recording

## Recommended Shortcuts

Here are suggested key combinations (adjust to avoid conflicts):

| Action | Suggested Key | Reason |
|--------|---------------|---------|
| Toggle | `Ctrl+Alt+Shift+R` | Easy to remember (R = Record), hard to conflict |
| Start  | `Ctrl+Alt+Shift+S` | S = Start |
| Stop   | `Ctrl+Alt+Shift+E` | E = sTop/End |

Or if you prefer single modifier:

| Action | Suggested Key | Reason |
|--------|---------------|---------|
| Toggle | `Super+R` | If Super key is available |
| Toggle | `Shift+F7` | Function key (less likely to conflict) |

## For Other Desktop Environments

### GNOME
Use GNOME Settings → Keyboard Shortcuts → Custom Shortcuts

### Sway/i3
Add to `~/.config/sway/config` or `~/.config/i3/config`:
```
bindsym $mod+r exec /home/rahul/.local/bin/whisper-recording-toggle toggle
```

### Hyprland
Add to `~/.config/hyprland/hyprland.conf`:
```
bind = SUPER, R, exec, /home/rahul/.local/bin/whisper-recording-toggle toggle
```

## Why This Works on Wayland

- **X11 limitation:** Wayland blocks global keyboard grabs for security
- **Our solution:** Uses signals instead of global hotkey events
- **Result:** Works on both X11 and Wayland without changes

This is the same approach used by Mumble, OBS, and other professional tools for Wayland compatibility.

## Next Steps

1. **Set up at least the Toggle shortcut** (`Ctrl+Alt+Shift+R`)
2. **Test it works** by pressing the shortcut while GUI is running
3. **(Optional) Add Start/Stop shortcuts** if you want finer control

That's it! Your recording control is now truly global and works on Wayland.
