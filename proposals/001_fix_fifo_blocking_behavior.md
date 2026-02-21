# CHANGE PROPOSAL #001: Fix FIFO Blocking Behavior

## Goal
Fix periodic hotkey breakage by restoring the original blocking FIFO read pattern.

## Rationale
The current non-blocking implementation with nested read loops causes FIFO state corruption after 7-8 successful reads. The hotkey daemon sends one command then closes the FIFO. The original blocking code naturally handled this by:
- Blocking in `open()` until daemon connects
- Reading one message
- Closing and looping back to wait for next connection

This is simpler, more reliable, and matches FIFO semantics.

## Minimal Change
File: `src/whisper_app/fifo_controller.py`
Lines: 158-209 (_read_loop method)

Change:
- Replace non-blocking os.open() with blocking open()
- Remove inner while loop (multiple reads from same fd)
- Keep one read per open cycle
- Re-open naturally waits for next writer

## Why Safe
- Restores proven working pattern from original code
- Simpler logic = fewer edge cases
- Single read per fd lifecycle prevents state corruption
- Blocking on open() is the standard FIFO pattern

## Test Plan
```bash
# Test FIFO communication 5 times rapidly
for i in {1..5}; do
  python3 /tmp/test_fifo.py
  sleep 0.5
done

# Check logs
journalctl --user -u whisper-gui -n 20 | grep "🔔"

# Should see all 15 commands received (3 per run × 5 runs)
```

## Size Check
Single method replacement, ~15 lines changed max.
Could not be simpler without being incomplete.

---

Status: PROPOSED
