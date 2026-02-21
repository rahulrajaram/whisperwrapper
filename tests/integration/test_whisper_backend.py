"""Optional integration tests that require the real Whisper backend."""

from __future__ import annotations

import os

from tests.helpers import ensure_whisper_module

ensure_whisper_module()


def test_transcription_service_loads_real_model():
    from whisper_app.config import WhisperRuntimeConfig
    from whisper_app.services.transcription import TranscriptionService

    model_name = os.environ.get("WHISPER_TEST_MODEL", "tiny")
    config = WhisperRuntimeConfig(model_name=model_name, headless=True)
    service = TranscriptionService(config)
    assert service.model is not None
