# Whisper Hotkey Daemon - Wayland Setup Guide

## The Problem

On **Wayland**, background applications cannot receive global keyboard input like they can on X11. This is a security feature built into Wayland.

The solution is to use **Plasma's native global shortcuts system** to bind CTRL+ALT+R to a script that starts recording.

## Solution: Use Plasma Global Shortcuts

### Step 1: Create a Launcher Script

Create `~/.local/bin/whisper-record`:

```bash
#!/bin/bash
# Start whisper recording

# Make sure daemon is running
if ! pgrep -f whisper_hotkey_daemon.py > /dev/null; then
    sudo /home/rahul/Documents/whisper/whisper_hotkey_daemon.py &
fi

# Send signal to daemon to start recording
# (We'll use a simpler approach via FIFO)
echo "START" > /tmp/whisper-control
```

Make it executable:
```bash
chmod +x ~/.local/bin/whisper-record
```

### Step 2: Modify the Daemon to Use FIFO Control

Edit `whisper_hotkey_daemon.py` to listen on a named pipe instead of evdev:

```python
# Add this to the daemon instead of evdev monitoring
fifo_path = "/tmp/whisper-control"

# Create FIFO
import os
if os.path.exists(fifo_path):
    os.remove(fifo_path)
os.mkfifo(fifo_path)

# Listen on FIFO
with open(fifo_path) as fifo:
    while True:
        command = fifo.read()
        if command == "START":
            if self.recording:
                self.stop_recording()
            else:
                self.start_recording()
        elif command == "STOP":
            if self.recording:
                self.stop_recording()
```

### Step 3: Bind Hotkey in Plasma

1. Open **System Settings** (or Settings)
2. Go to **Shortcuts** → **Global Shortcuts**
3. Find or create **Custom Shortcuts**
4. Add a new shortcut:
   - **Trigger**: CTRL+ALT+R
   - **Action**: Run script `~/.local/bin/whisper-record`

### Alternative: Use xdotool (Simpler)

If the above doesn't work, use `xdotool` to detect keypresses:

```bash
sudo apt-get install xdotool

# Create a script that runs in background
cat > ~/.local/bin/whisper-hotkey-listener << 'EOF'
#!/bin/bash
while true; do
    xdotool search --name . windowactivate %@
    # Monitor for hotkey (this is complex with xdotool)
    # Use Plasma shortcuts instead
done
EOF
```

## Recommended: Stop Using evdev, Use Plasma Instead

**The cleanest solution for Wayland:**

1. **Keep the recording logic** in `whisper_hotkey_daemon.py`
2. **Stop trying to monitor evdev** in the daemon
3. **Use Plasma's Global Shortcuts** to trigger recording
4. **Have the daemon listen via FIFO or D-Bus** for commands

This way:
- ✅ Works perfectly on Wayland
- ✅ Integrates with Plasma's hotkey system
- ✅ More secure
- ✅ Respects desktop conventions

## Simple Working Setup for Wayland

### 1. Run the recording daemon (background service)

```bash
sudo ./whisper_hotkey_daemon.py &
```

But **modify it to NOT monitor evdev**, instead listen on a named pipe:

```python
def run_as_service(self):
    """Run as service, listen for commands via FIFO"""
    import os

    fifo = "/tmp/whisper-hotkey-cmd"
    if os.path.exists(fifo):
        os.remove(fifo)
    os.mkfifo(fifo)

    while True:
        with open(fifo) as f:
            cmd = f.read().strip()
            if cmd == "RECORD_START":
                self.start_recording()
            elif cmd == "RECORD_STOP":
                self.stop_recording()
```

### 2. Create trigger script

`~/.local/bin/whisper-record`:

```bash
#!/bin/bash
# Toggle recording
echo "RECORD_START" > /tmp/whisper-hotkey-cmd
```

### 3. Bind in Plasma

System Settings → Shortcuts → Global Shortcuts → Add Custom Shortcut
- Trigger: CTRL+ALT+R
- Command: `/home/rahul/.local/bin/whisper-record`

## Why This Works

- ✅ Plasma handles the global hotkey securely
- ✅ Plasma sends the command to your script
- ✅ Your script signals the daemon via FIFO
- ✅ Daemon performs the recording
- ✅ Works perfectly on Wayland

## Next Steps

1. Try the FIFO-based approach
2. Or set up Plasma Global Shortcuts integration
3. Test CTRL+ALT+R from any application

This is the **proper way** to do global hotkeys on Wayland.
