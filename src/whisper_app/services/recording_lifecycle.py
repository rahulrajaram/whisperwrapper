"""Agnostic side-effect adapter for recording lifecycle boundaries."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol, Sequence

from ..config import RecordingLifecycleConfig

logger = logging.getLogger(__name__)


class RecordingLifecycleEvent(Enum):
    STARTING = "starting"
    STOPPED = "stopped"


class RecordingLifecycleAdapter(Protocol):
    def before_recording_start(self) -> None:
        """Run immediately before the recorder opens its input stream."""

    def after_recording_stop(self) -> None:
        """Run immediately after capture ends and before transcription."""


LifecycleCommandRunner = Callable[[Sequence[str], float], subprocess.CompletedProcess[str]]


def _run_lifecycle_command(
    command: Sequence[str], timeout_seconds: float
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )


@dataclass(frozen=True)
class CommandRecordingLifecycleAdapter:
    """Dispatch lifecycle events to one configured executable, without a shell."""

    config: RecordingLifecycleConfig
    runner: LifecycleCommandRunner = _run_lifecycle_command

    def before_recording_start(self) -> None:
        self._dispatch(RecordingLifecycleEvent.STARTING)

    def after_recording_stop(self) -> None:
        self._dispatch(RecordingLifecycleEvent.STOPPED)

    def _dispatch(self, event: RecordingLifecycleEvent) -> None:
        if not self.config.command:
            return
        command = (*self.config.command, event.value)
        try:
            result = self.runner(command, self.config.timeout_seconds)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("Recording lifecycle hook %s failed: %s", event.value, exc)
            return
        if result.returncode != 0:
            detail = result.stderr.strip() or f"exit status {result.returncode}"
            logger.warning("Recording lifecycle hook %s failed: %s", event.value, detail)


__all__ = [
    "CommandRecordingLifecycleAdapter",
    "RecordingLifecycleAdapter",
    "RecordingLifecycleEvent",
]
