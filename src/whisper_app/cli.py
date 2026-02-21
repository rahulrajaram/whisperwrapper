#!/usr/bin/env python3
"""CLI entry point built on top of the new recording controller."""

from __future__ import annotations

import argparse
import itertools
import os
import signal
import sys
import time
from typing import Optional

from .config import WhisperRuntimeConfig
from .controllers import RecordingEventCallbacks, WhisperRecordingController


class WhisperCLI:
    """Backwards-compatible CLI facade built on the new services."""

    def __init__(self, headless: bool = False, force_configure: bool = False, debug: bool = False):
        self.headless = headless
        self.debug = debug
        self._latest_transcript: Optional[str] = None
        self.spinner_running = False
        self.spinner_thread = None

        self._configure_audio_env()
        self.runtime_config = WhisperRuntimeConfig(headless=headless, debug=debug)
        self._callbacks = RecordingEventCallbacks(
            on_start=self._on_recording_start,
            on_stop=self._on_recording_stop,
            on_result=self._on_transcription_result,
            on_error=self._on_error,
        )
        self.controller = WhisperRecordingController(
            runtime_config=self.runtime_config,
            callbacks=self._callbacks,
        )

        if force_configure or self.controller.audio_service.input_device_index is None:
            self._select_microphone()

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------
    @property
    def recording(self) -> bool:
        return self.controller.recording

    def start_recording(self) -> None:
        self.controller.start()

    def stop_recording(self) -> Optional[str]:
        text = self.controller.stop()
        if text:
            self._write_to_fifo(text)
        return text

    def cleanup(self) -> None:
        self.controller.cleanup()

    # ------------------------------------------------------------------
    # Callback hooks
    # ------------------------------------------------------------------
    def _on_recording_start(self) -> None:
        if not self.headless:
            print("🎤 Recording started... Press ENTER to stop.")

    def _on_recording_stop(self) -> None:
        if not self.headless:
            print("⏹️  Recording stopped. Processing...")

    def _on_transcription_result(self, text: str) -> None:
        self._latest_transcript = text
        if not self.headless:
            print(f"\n📝 Transcription:\n   {text}")

    def _on_error(self, message: str) -> None:
        print(f"⚠️  Recording error: {message}")

    # ------------------------------------------------------------------
    # Microphone configuration
    # ------------------------------------------------------------------
    def _configure_audio_env(self) -> None:
        os.environ.setdefault('ALSA_PCM_CARD', 'default')
        os.environ.setdefault('ALSA_PCM_DEVICE', '0')
        if self.headless:
            os.environ.setdefault('JACK_NO_AUDIO_RESERVATION', '1')
            os.environ.setdefault('PULSE_LATENCY_MSEC', '30')

    def _select_microphone(self) -> None:
        audio_service = self.controller.audio_service
        devices = audio_service.list_input_devices()
        if not devices:
            print("❌ No input devices found")
            sys.exit(1)

        if self.headless:
            audio_service.input_device_index = audio_service.select_default_device()
            return

        print("\n🎤 Available input devices:")
        default_idx = audio_service.select_default_device()
        for row, device in enumerate(devices):
            marker = " (DEFAULT)" if device.index == default_idx else ""
            print(f"  {row}: {device.name}{marker}")

        while True:
            try:
                choice = input(
                    f"\nSelect microphone (0-{len(devices)-1}, or press ENTER for default): "
                ).strip()
                if choice == "" and default_idx is not None:
                    audio_service.input_device_index = default_idx
                    print(f"🎯 Using default input device: {default_idx}")
                    return

                idx = int(choice)
                if 0 <= idx < len(devices):
                    audio_service.input_device_index = devices[idx].index
                    print(f"🎯 Selected: {devices[idx].name}")
                    return
                print("Please enter a valid device number")
            except ValueError:
                print("Please enter a number or press ENTER for default")
            except KeyboardInterrupt:
                print("\nExiting...")
                sys.exit(0)

    # ------------------------------------------------------------------
    # CLI UX helpers
    # ------------------------------------------------------------------
    def run_headless(self) -> Optional[str]:
        try:
            self.start_recording()
            self._start_spinner()
            input()
            self._stop_spinner()
            return self.stop_recording()
        finally:
            self._stop_spinner()
            self.cleanup()

    def run(self) -> None:
        if self.headless:
            self.run_headless()
            return

        print("🎙️  Whisper Real-time CLI")
        print("=" * 30)
        print("Commands:\n  ENTER - Start/Stop recording\n  'quit' - Exit")
        print("=" * 30)

        try:
            while True:
                user_input = input("\nPress ENTER to start recording (or 'quit' to exit): ").strip()
                if user_input.lower() in {"quit", "exit", "q"}:
                    break
                if not self.recording:
                    self.start_recording()
                    input()
                    self.stop_recording()
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
            print("\nGoodbye!")

    def _start_spinner(self) -> None:
        if not self.headless:
            return
        self.spinner_running = True

        def spin():
            for frame in itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧']):
                if not self.spinner_running:
                    break
                sys.stdout.write(f"\r{frame} Recording... Press ENTER to stop")
                sys.stdout.flush()
                time.sleep(0.1)
            sys.stdout.write('\r' + ' ' * 40 + '\r')
            sys.stdout.flush()

        import threading

        self.spinner_thread = threading.Thread(target=spin, daemon=True)
        self.spinner_thread.start()

    def _stop_spinner(self) -> None:
        if not self.spinner_running:
            return
        self.spinner_running = False
        if self.spinner_thread and self.spinner_thread.is_alive():
            self.spinner_thread.join(timeout=0.5)

    # ------------------------------------------------------------------
    def signal_handler(self, sig, frame) -> None:  # pragma: no cover - signal path
        if self.recording:
            transcript = self.stop_recording()
            if transcript:
                self._write_to_fifo(transcript)
        self.cleanup()
        sys.exit(0)

    def _write_to_fifo(self, text: str) -> None:
        fifo_path = os.environ.get('WHISPER_TRANSCRIPT_FIFO')
        if not fifo_path or not text:
            return
        try:
            with open(fifo_path, 'w') as fifo:
                fifo.write(text)
        except OSError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Whisper Real-time Speech-to-Text CLI")
    parser.add_argument('--configure', action='store_true', help='Configure microphone settings')
    parser.add_argument('--headless', action='store_true', help='Run a single headless session')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    cli = WhisperCLI(headless=args.headless, force_configure=args.configure, debug=args.debug)
    if args.headless:
        cli.run_headless()
    elif args.configure:
        print("✅ Configuration complete!")
    else:
        cli.run()


if __name__ == "__main__":
    main()
