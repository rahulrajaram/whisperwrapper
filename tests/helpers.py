"""Shared helpers for Whisper test instrumentation."""

from __future__ import annotations

import importlib.machinery
import os
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType

LOG_PATH = Path(os.environ.get("WHISPER_TEST_LOG", ".whisper_test.log"))


def log_whisper_event(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(f"[{timestamp}] {message}\n")


class _StubSegment:
    """Mimics a faster-whisper segment namedtuple."""

    def __init__(self, text: str):
        self.text = text


class _StubInfo:
    """Mimics a faster-whisper TranscriptionInfo."""

    language = "en"
    language_probability = 0.99


class _StubWhisperModel:
    """Mimics faster_whisper.WhisperModel for tests."""

    def __init__(self, model_size_or_path: str, device: str = "cpu", compute_type: str = "int8", **kwargs):
        self.model_size = model_size_or_path
        self.device = device
        self.compute_type = compute_type

    def transcribe(self, filename: str, **kwargs):
        segments = [_StubSegment(f"[stub transcription:{self.model_size}]")]
        return iter(segments), _StubInfo()


def _install_faster_whisper_stub() -> ModuleType:
    """Install a lightweight faster_whisper stub so integration tests always run."""

    stub = ModuleType("faster_whisper")
    stub.__version__ = "test-stub"  # type: ignore[attr-defined]
    stub.__faster_whisper_stub__ = True  # type: ignore[attr-defined]
    stub.__file__ = str(LOG_PATH)
    stub.__spec__ = importlib.machinery.ModuleSpec("faster_whisper", loader=None)  # type: ignore[arg-type]
    stub.WhisperModel = _StubWhisperModel  # type: ignore[attr-defined]
    return stub


def _patch_transcription_module(module: ModuleType) -> None:
    transcription = sys.modules.get("whisper_app.services.transcription")
    if transcription is not None:
        setattr(transcription, "WhisperModel", module.WhisperModel)  # type: ignore[attr-defined]


def _load_real_faster_whisper() -> ModuleType | None:
    try:
        import faster_whisper  # type: ignore
    except ImportError:
        log_whisper_event("Real faster-whisper import failed; falling back to stub backend")
        return None

    if getattr(faster_whisper, "WhisperModel", None) is None:
        log_whisper_event("faster_whisper module missing WhisperModel; falling back to stub backend")
        return None

    log_whisper_event("Real faster-whisper detected; using installed backend")
    return faster_whisper  # type: ignore[name-defined]


def ensure_whisper_module() -> ModuleType:
    """Guarantee that a usable faster_whisper module (real or stub) is importable."""

    force_real = os.environ.get("WHISPER_TESTS_FORCE_REAL") == "1"
    module = sys.modules.get("faster_whisper")

    if module is not None:
        is_stub = getattr(module, "__faster_whisper_stub__", False)
        if force_real and is_stub:
            real = _load_real_faster_whisper()
            if real is not None:
                sys.modules["faster_whisper"] = real
                _patch_transcription_module(real)
                return real
        if not force_real and not is_stub:
            module = _install_faster_whisper_stub()
            sys.modules["faster_whisper"] = module
            _patch_transcription_module(module)
            log_whisper_event("Using faster-whisper stub backend for tests (overriding real module)")
        return module

    if force_real:
        real = _load_real_faster_whisper()
        if real is not None:
            sys.modules["faster_whisper"] = real
            _patch_transcription_module(real)
            return real
        log_whisper_event("WHISPER_TESTS_FORCE_REAL=1 but real backend unavailable; using stub")

    stub = _install_faster_whisper_stub()
    sys.modules["faster_whisper"] = stub
    _patch_transcription_module(stub)
    log_whisper_event("Using faster-whisper stub backend for tests")
    return stub


def install_whisper_stub() -> ModuleType:
    """Public helper for tests that need direct control over the stub."""

    stub = _install_faster_whisper_stub()
    sys.modules["faster_whisper"] = stub
    _patch_transcription_module(stub)
    log_whisper_event("faster-whisper stub installed via tests.helpers.install_whisper_stub")
    return stub
