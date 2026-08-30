"""Tests for the external recording-lifecycle boundary."""

from __future__ import annotations

import subprocess

from whisper_app.config import RecordingLifecycleConfig
from whisper_app.services.recording_lifecycle import CommandRecordingLifecycleAdapter


def test_adapter_dispatches_ordered_events_without_a_shell():
    calls = []

    def runner(command, timeout):
        calls.append((tuple(command), timeout))
        return subprocess.CompletedProcess(command, 0, "", "")

    adapter = CommandRecordingLifecycleAdapter(
        RecordingLifecycleConfig(("/usr/bin/example-hook", "--quiet"), 4.0),
        runner,
    )

    adapter.before_recording_start()
    adapter.after_recording_stop()

    assert calls == [
        (("/usr/bin/example-hook", "--quiet", "starting"), 4.0),
        (("/usr/bin/example-hook", "--quiet", "stopped"), 4.0),
    ]


def test_adapter_is_a_noop_without_a_configured_command():
    calls = []
    adapter = CommandRecordingLifecycleAdapter(
        RecordingLifecycleConfig(),
        lambda command, timeout: calls.append((command, timeout)),
    )

    adapter.before_recording_start()
    adapter.after_recording_stop()

    assert calls == []


def test_adapter_is_fail_open_for_hook_errors():
    def failing_runner(command, timeout):
        raise subprocess.TimeoutExpired(command, timeout)

    adapter = CommandRecordingLifecycleAdapter(
        RecordingLifecycleConfig(("/usr/bin/example-hook",), 0.1),
        failing_runner,
    )

    adapter.before_recording_start()
    adapter.after_recording_stop()
