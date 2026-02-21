# Whisper GUI - Isolated Python Environment & Systemd Setup

## Overview

Whisper now uses an **isolated Python virtual environment** to keep dependencies separate from your system Python. The app is started via **systemd** (the Linux system service manager) on login, ensuring clean isolation and automatic startup.

## Architecture

```
System Login
    ↓
systemd user service (whisper-gui.service)
    ↓
Activates ~/.config/systemd/user/whisper-gui.service
    ↓
Executes: ~/Documents/whisper/venv/bin/python3 whisper_gui.py
    ↓
Isolated Virtual Environment (no system Python dependencies)
    ↓
Whisper GUI appears in system tray 🎤
```

## Quick Setup

### One-Command Installation

```bash
cd ~/Documents/whisper
./setup_venv_systemd.sh
```

This will:
1. ✅ Create a Python virtual environment in `./venv`
2. ✅ Install all dependencies (openai-whisper, PyQt6, pyaudio, etc.)
3. ✅ Create systemd service configuration
4. ✅ Enable autostart on next login

After running, **log out and log back in** - Whisper will appear in the system tray automatically.

## What's Included

### Virtual Environment (`./venv/`)

Located in your project directory:
```
~/Documents/whisper/venv/
├── bin/
│   ├── python3          ← Isolated Python interpreter
│   ├── pip              ← Isolated package manager
│   └── activate         ← Activation script
├── lib/
│   └── python3.11/site-packages/  ← Isolated dependencies
└── pyvenv.cfg
```

**Key Benefits:**
- ✅ Completely isolated from system Python
- ✅ No conflicts with other Python projects
- ✅ Easy to clean up (just delete `venv/` folder)
- ✅ Can have different Python versions per project
- ✅ Dependencies won't break if system updates

### Systemd Service (`whisper-gui.service`)

Installed to: `~/.config/systemd/user/whisper-gui.service`

**Features:**
- ✅ Auto-starts on login (user session)
- ✅ Automatically restarts on crash (5-second delay)
- ✅ Logs to systemd journal (accessible via `journalctl`)
- ✅ Proper KDE integration
- ✅ Handles environment variables correctly

## Usage

### Manual Start (Without Logging Out)

```bash
systemctl --user start whisper-gui
```

### Check Service Status

```bash
systemctl --user status whisper-gui
```

Output:
```
● whisper-gui.service - Whisper Voice Recording GUI
     Loaded: loaded (/home/rahul/.config/systemd/user/whisper-gui.service; enabled; vendor preset: enabled)
     Active: active (running) since Sat 2025-11-02 14:30:45 UTC; 2min 15s ago
   Main PID: 12345 (python3)
     CGroup: /user.slice/user-1000.slice/user@1000.service/app.slice/whisper-gui.service
             └─12345 /home/rahul/Documents/whisper/venv/bin/python3 /home/rahul/Documents/whisper/whisper_gui.py
```

### View Service Logs

```bash
# View recent logs
journalctl --user -u whisper-gui

# Follow logs in real-time (like tail -f)
journalctl --user -u whisper-gui -f

# View logs from the last 1 hour
journalctl --user -u whisper-gui --since "1 hour ago"

# View only errors
journalctl --user -u whisper-gui --priority err
```

### Stop Service

```bash
systemctl --user stop whisper-gui
```

### Restart Service

```bash
systemctl --user restart whisper-gui
```

## Virtual Environment Usage

### Activate Virtual Environment Manually

```bash
cd ~/Documents/whisper
source venv/bin/activate
```

You'll see the prompt change to:
```
(venv) rahul@machine:~/Documents/whisper$
```

### Deactivate Virtual Environment

```bash
deactivate
```

### Install New Packages

```bash
# Activate venv first
source venv/bin/activate

# Install package
pip install package-name

# Deactivate
deactivate
```

### Update Venv Python Packages

```bash
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --upgrade
deactivate
```

## File Locations

```
~/Documents/whisper/
├── venv/                           ← Virtual environment (isolated Python)
│   ├── bin/python3                 ← Isolated Python executable
│   ├── bin/pip                     ← Isolated pip
│   └── lib/python3.11/site-packages/  ← Isolated dependencies
├── whisper-gui.service             ← Systemd service file (template)
├── setup_venv_systemd.sh           ← Setup script (what you ran)
├── whisper_gui.py                  ← Main application
├── whisper_cli.py                  ← CLI recording engine
└── requirements.txt                ← Python dependencies list

~/.config/systemd/user/
└── whisper-gui.service             ← Installed systemd service
```

## Troubleshooting

### Service Won't Start

**Check systemd status:**
```bash
systemctl --user status whisper-gui
journalctl --user -u whisper-gui -n 50
```

**Common issues:**
- Python path wrong: Check that `venv/bin/python3` exists
- File permissions: Run `ls -l whisper_gui.py` - should be executable
- Service file not reloaded: Run `systemctl --user daemon-reload`

### Virtual Environment Not Working

**Check venv exists:**
```bash
ls -la venv/bin/python3
```

**Recreate venv if needed:**
```bash
rm -rf venv/
./setup_venv_systemd.sh
```

### Dependencies Missing

**Reinstall requirements:**
```bash
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

**Update requirements after changes:**
```bash
source venv/bin/activate
pip install --upgrade openai-whisper
pip freeze > requirements.txt
deactivate
```

### Can't Find systemd Service

**Check it's installed:**
```bash
ls ~/.config/systemd/user/whisper-gui.service
```

**If missing, reinstall:**
```bash
./setup_venv_systemd.sh
```

### Logs Not Appearing

**Check journalctl works:**
```bash
journalctl --user -u whisper-gui
```

**If nothing shows, service might not have started:**
```bash
systemctl --user start whisper-gui
sleep 2
journalctl --user -u whisper-gui
```

## Disable Autostart

### Temporary (Until Next Reboot)

```bash
systemctl --user stop whisper-gui
```

### Permanent

```bash
systemctl --user disable whisper-gui
```

To re-enable:
```bash
systemctl --user enable whisper-gui
systemctl --user start whisper-gui
```

## Advanced Configuration

### Modify Autostart Behavior

Edit `~/.config/systemd/user/whisper-gui.service`:

```bash
nano ~/.config/systemd/user/whisper-gui.service
```

After changes:
```bash
systemctl --user daemon-reload
systemctl --user restart whisper-gui
```

### Add Custom Environment Variables

Edit the service file and add under `[Service]`:

```ini
Environment="CUSTOM_VAR=value"
Environment="ANOTHER_VAR=another_value"
```

### Change Restart Behavior

Default is "restart on failure with 5-second delay". To change:

```ini
Restart=always           # Always restart
RestartSec=10           # Wait 10 seconds before restart
```

### Run on Specific Targets

Current: `graphical-session.target` (normal login)

Other options:
- `graphical.target` - Full graphical session
- `multi-user.target` - System startup (requires root)

## Security & Isolation

### Why Virtual Environment?

1. **Isolation**: Dependencies won't interfere with system or other projects
2. **Cleanliness**: Easy to remove (just delete `venv/`)
3. **Reproducibility**: Same versions across machines
4. **Updates**: System Python updates won't break Whisper
5. **Testing**: Can test with different Python versions

### Why Systemd?

1. **Clean startup**: Integrated with system login
2. **Automatic restart**: App restarts if it crashes
3. **Logging**: All output captured in journal
4. **User-level**: No need for root/sudo
5. **Resource management**: Systemd handles process groups
6. **Standard**: Uses standard Linux service management

## Comparison: Before vs After

### Before (Direct Terminal)
```bash
cd ~/Documents/whisper
python3 whisper_gui.py
```
- Manual startup each time
- No autostart
- Mixed with system Python

### After (Virtual Environment + Systemd)
```bash
# Just one-time setup
./setup_venv_systemd.sh

# Then autostart on every login
# No action needed!
```
- Automatic startup on login
- Isolated Python environment
- Managed by systemd
- Logs available in journal

## Performance

- **Startup Time**: Systemd adds <1 second
- **Memory**: Venv adds ~0-5MB (loaded once at login)
- **CPU**: No impact when idle
- **Disk**: Venv uses ~1-2GB (includes Whisper model cache)

## Monitoring

### Watch Logs Live

```bash
journalctl --user -u whisper-gui -f
```

### Check Resource Usage

```bash
systemctl --user status whisper-gui
ps aux | grep "[p]ython3.*whisper"
```

### Integration with System Tools

Works with standard Linux tools:
```bash
# systemctl
systemctl --user list-units | grep whisper-gui

# journalctl
journalctl --user | grep whisper-gui

# ps
ps aux | grep whisper

# Resource monitoring
top
htop
```

## Next Steps

1. ✅ Run `./setup_venv_systemd.sh`
2. ✅ Log out and log back in
3. ✅ Whisper appears in system tray 🎤
4. ✅ Check logs: `journalctl --user -u whisper-gui -f`
5. ✅ Use normally - autostart handles everything!

## Support

### Get Help

```bash
# Check service status
systemctl --user status whisper-gui

# View detailed logs
journalctl --user -u whisper-gui -n 100

# Manual venv activation
source venv/bin/activate
python3 --version
deactivate
```

### Common Commands Reference

```bash
# Start/Stop/Restart
systemctl --user start whisper-gui
systemctl --user stop whisper-gui
systemctl --user restart whisper-gui

# Status & Logs
systemctl --user status whisper-gui
journalctl --user -u whisper-gui

# Enable/Disable
systemctl --user enable whisper-gui
systemctl --user disable whisper-gui

# Venv
source ~/Documents/whisper/venv/bin/activate
deactivate
```

Enjoy your isolated, automatically-started Whisper! 🚀
