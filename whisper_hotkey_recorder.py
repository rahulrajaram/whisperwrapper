#!/usr/bin/env python3
"""
Whisper hotkey recorder helper

This script is called by the hotkey daemon to perform the actual recording.
It handles:
- Starting a recording session
- Capturing audio from microphone
- Transcribing with Whisper
- Saving transcription to clipboard

Usage:
    Normally called by whisper_hotkey_daemon.py
    Can also be run standalone for testing: ./whisper_hotkey_recorder.py
"""

import sys
import os
import tempfile
import subprocess
from pathlib import Path
from contextlib import redirect_stderr
import io
import time

# Import whisper CLI
sys.path.insert(0, str(Path(__file__).parent))

try:
    from whisper_cli import WhisperCLI
except ImportError as e:
    print(f"Error importing WhisperCLI: {e}", file=sys.stderr)
    sys.exit(1)


class WhisperHotkeyRecorder:
    """Record audio and save transcription to clipboard"""

    def __init__(self):
        self.whisper_cli = None
        self.transcription = None

    def _copy_to_clipboard(self, text):
        """Copy text to system clipboard"""
        if not text:
            return False

        try:
            # Try xclip first (most common)
            process = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            process.communicate(input=text, timeout=2)

            if process.returncode == 0:
                return True

        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"xclip error: {e}", file=sys.stderr)

        try:
            # Try wl-copy (Wayland clipboard)
            process = subprocess.Popen(
                ["wl-copy"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            process.communicate(input=text, timeout=2)

            if process.returncode == 0:
                return True

        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"wl-copy error: {e}", file=sys.stderr)

        try:
            # Try xsel (alternative)
            process = subprocess.Popen(
                ["xsel", "-bi"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            process.communicate(input=text, timeout=2)

            if process.returncode == 0:
                return True

        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"xsel error: {e}", file=sys.stderr)

        return False

    def record_and_transcribe(self):
        """Perform recording and transcription"""
        try:
            # Initialize WhisperCLI in headless mode with debug disabled
            self.whisper_cli = WhisperCLI(headless=True, debug=False)

            # Suppress output during recording
            print("Recording...", file=sys.stderr)

            # Start recording
            self.whisper_cli.start_recording()

            # Wait for SIGTERM (sent by hotkey daemon)
            # The daemon will send SIGTERM when user presses RETURN/ESC
            import signal

            def wait_for_stop(sig, frame):
                self.whisper_cli.stop_recording()
                raise KeyboardInterrupt

            signal.signal(signal.SIGTERM, wait_for_stop)

            # Wait indefinitely - process will be terminated by daemon
            while True:
                time.sleep(0.1)

        except KeyboardInterrupt:
            # Normal exit path
            if self.whisper_cli and self.whisper_cli.recording:
                self.transcription = self.whisper_cli.stop_recording()
            sys.exit(0)

        except Exception as e:
            print(f"Error during recording: {e}", file=sys.stderr)
            if self.whisper_cli:
                self.whisper_cli.cleanup()
            sys.exit(1)

        finally:
            # Clean up
            if self.whisper_cli:
                self.whisper_cli.cleanup()

            # Save to clipboard if we got a transcription
            if self.transcription:
                success = self._copy_to_clipboard(self.transcription)
                if success:
                    print(f"✅ Saved to clipboard: {self.transcription}", file=sys.stderr)
                else:
                    print(
                        f"⚠️  Could not copy to clipboard (no xclip/wl-copy/xsel found): {self.transcription}",
                        file=sys.stderr,
                    )


def main():
    recorder = WhisperHotkeyRecorder()
    recorder.record_and_transcribe()


if __name__ == "__main__":
    main()
