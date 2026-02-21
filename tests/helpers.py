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


def _install_whisper_stub() -> ModuleType:
    """Install a lightweight Whisper stub so integration tests always run."""

    class _StubModel:
        def __init__(self, model_name: str, device: str | None = None):
            self.model_name = model_name
            self.device = device

        def transcribe(self, filename: str):
            return {"text": f"[stub transcription:{self.model_name}]"}

    stub = ModuleType("whisper")
    stub.__version__ = "test-stub"  # type: ignore[attr-defined]
    stub.__whisper_stub__ = True  # type: ignore[attr-defined]
    stub.__file__ = str(LOG_PATH)
    stub.__spec__ = importlib.machinery.ModuleSpec("whisper", loader=None)  # type: ignore[arg-type]

    def load_model(model_name: str, device: str | None = None, **_):
        return _StubModel(model_name=model_name, device=device)

    stub.load_model = load_model  # type: ignore[attr-defined]
    return stub


def _patch_transcription_module(module: ModuleType) -> None:
    transcription = sys.modules.get("whisper_app.services.transcription")
    if transcription is not None:
        setattr(transcription, "whisper", module)


def _load_real_whisper() -> ModuleType | None:
    try:
        import whisper  # type: ignore
    except ImportError:
        log_whisper_event("Real Whisper import failed; falling back to stub backend")
        return None

    if getattr(whisper, "load_model", None) is None:
        log_whisper_event("Whisper module missing load_model; falling back to stub backend")
        return None

    spec = getattr(whisper, "__spec__", None)
    if spec is None and not getattr(whisper, "__file__", None):
        log_whisper_event("Whisper module missing spec/file; falling back to stub backend")
        return None

    log_whisper_event("Real Whisper detected; using installed backend")
    return whisper  # type: ignore[name-defined]


def ensure_whisper_module() -> ModuleType:
    """Guarantee that a usable Whisper module (real or stub) is importable."""

    force_real = os.environ.get("WHISPER_TESTS_FORCE_REAL") == "1"
    module = sys.modules.get("whisper")

    if module is not None:
        is_stub = getattr(module, "__whisper_stub__", False)
        if force_real and is_stub:
            real = _load_real_whisper()
            if real is not None:
                sys.modules["whisper"] = real
                _patch_transcription_module(real)
                return real
        if not force_real and not is_stub:
            module = _install_whisper_stub()
            sys.modules["whisper"] = module
            _patch_transcription_module(module)
            log_whisper_event("Using whisper stub backend for tests (overriding real module)")
        return module

    if force_real:
        real = _load_real_whisper()
        if real is not None:
            sys.modules["whisper"] = real
            _patch_transcription_module(real)
            return real
        log_whisper_event("WHISPER_TESTS_FORCE_REAL=1 but real backend unavailable; using stub")

    stub = _install_whisper_stub()
    sys.modules["whisper"] = stub
    _patch_transcription_module(stub)
    log_whisper_event("Using whisper stub backend for tests")
    return stub


def install_whisper_stub() -> ModuleType:
    """Public helper for tests that need direct control over the stub."""

    stub = _install_whisper_stub()
    sys.modules["whisper"] = stub
    _patch_transcription_module(stub)
    log_whisper_event("Whisper stub installed via tests.helpers.install_whisper_stub")
    return stub
