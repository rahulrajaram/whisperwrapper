"""Tests for shared configuration helpers."""

from __future__ import annotations

from whisper_app.config import (
    RECORDING_LIFECYCLE_COMMAND_ENV,
    SYSTEM_INPUT_ROUTE,
    RecordingLifecycleConfig,
    WhisperPaths,
    load_microphone_config,
    recording_lifecycle_command_from_environment,
    save_microphone_config,
)


def test_recording_lifecycle_command_is_optional_and_shell_free():
    assert recording_lifecycle_command_from_environment({}) == ()
    assert recording_lifecycle_command_from_environment(
        {RECORDING_LIFECYCLE_COMMAND_ENV: '/usr/bin/tool --label "two words"'}
    ) == ("/usr/bin/tool", "--label", "two words")
    assert RecordingLifecycleConfig(command=("/usr/bin/tool",)).command == ("/usr/bin/tool",)


def test_invalid_recording_lifecycle_command_fails_closed():
    assert (
        recording_lifecycle_command_from_environment(
            {RECORDING_LIFECYCLE_COMMAND_ENV: "'unterminated"}
        )
        == ()
    )


def test_whisper_paths_resolves_locations(tmp_path):
    paths = WhisperPaths(base_dir=tmp_path)

    assert paths.fifo_path == tmp_path / "control.fifo"
    assert paths.config_path == tmp_path / "config"
    assert paths.history_path == tmp_path / "gui_history.json"
    assert paths.lock_path == tmp_path / "app.lock"


def test_microphone_config_roundtrip(tmp_path):
    paths = WhisperPaths(base_dir=tmp_path)
    route = "pipewire:alsa_input.usb-TONOR"

    save_microphone_config(paths, route)

    assert load_microphone_config(paths) == route


def test_legacy_numeric_microphone_config_migrates_to_system_default(tmp_path):
    paths = WhisperPaths(base_dir=tmp_path)
    paths.config_path.write_text('{"input_device_index": 7}')

    assert load_microphone_config(paths) == SYSTEM_INPUT_ROUTE


def test_legacy_named_microphone_config_migrates_to_stable_direct_route(tmp_path):
    paths = WhisperPaths(base_dir=tmp_path)
    paths.config_path.write_text('{"input_device_name": "USB microphone"}')

    assert load_microphone_config(paths) == "portaudio:USB microphone"


def test_legacy_logical_microphone_config_migrates_to_system_default(tmp_path):
    paths = WhisperPaths(base_dir=tmp_path)
    paths.config_path.write_text('{"input_device_name": "pulse"}')

    assert load_microphone_config(paths) == SYSTEM_INPUT_ROUTE


def test_microphone_config_handles_missing_and_invalid(tmp_path):
    paths = WhisperPaths(base_dir=tmp_path)

    # Missing file follows the desktop's default input policy.
    assert load_microphone_config(paths) == SYSTEM_INPUT_ROUTE

    # Invalid payload follows the same safe policy without raising.
    paths.config_path.write_text("not json")
    assert load_microphone_config(paths) == SYSTEM_INPUT_ROUTE


def test_invalid_microphone_route_is_saved_as_system_default(tmp_path):
    paths = WhisperPaths(base_dir=tmp_path)

    save_microphone_config(paths, "pulse")

    assert load_microphone_config(paths) == SYSTEM_INPUT_ROUTE
