"""Wrapper around IPC controllers to emit structured callbacks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List

import logging

from .ipc_controller import CommandController


logger = logging.getLogger(__name__)

CommandHandler = Callable[[str], None]


@dataclass
class CommandBus:
    controller: CommandController
    _subscribers: Dict[str, List[CommandHandler]] = field(default_factory=lambda: {
        "start": [],
        "stop": [],
        "toggle": [],
    })

    def __post_init__(self) -> None:
        self.controller.on_command_received = self._dispatch

    def subscribe(self, command: str, handler: CommandHandler) -> None:
        if command not in self._subscribers:
            raise ValueError(f"Unsupported command: {command}")
        logger.debug("Subscribing handler to command '%s'", command)
        self._subscribers[command].append(handler)

    def start(self) -> None:
        logger.info("Starting command controller %s", self.controller.__class__.__name__)
        self.controller.start()

    def stop(self) -> None:
        logger.info("Stopping command controller %s", self.controller.__class__.__name__)
        self.controller.stop()

    def _dispatch(self, command: str) -> None:
        handlers = self._subscribers.get(command, [])
        logger.info("Dispatching command '%s' to %d handler(s)", command, len(handlers))
        for idx, handler in enumerate(handlers):
            try:
                logger.debug("Calling handler %d/%d for command '%s'", idx + 1, len(handlers), command)
                handler(command)
                logger.debug("Handler %d/%d completed successfully", idx + 1, len(handlers))
            except Exception as e:
                logger.exception("Handler %d/%d failed for command '%s': %s", idx + 1, len(handlers), command, e)


__all__ = ["CommandBus"]
