"""Public failures preserve actionable messages without exposing runtime details."""
from OCR.errors import ProviderResourceError, ProviderInitializationError, public_error_message
from OCR.providers.paddle_vl import PaddleVLProvider
import pytest


def test_paddle_memory_failure_is_safe_and_actionable(settings, monkeypatch):
    import OCR.providers.paddle_vl as module
    message = "PaddleOCR-VL requires a higher-memory container."
    monkeypatch.setattr(module, "paddle_memory_issue", lambda settings: message)
    with pytest.raises(ProviderResourceError) as failure:
        PaddleVLProvider(settings).initialize()
    assert public_error_message(failure.value) == message


def test_unapproved_runtime_details_remain_private():
    exc = ProviderInitializationError("secret checkpoint path", provider="paddle_vl")
    assert "secret" not in public_error_message(exc)
    assert "PaddleOCR-VL initialization" in public_error_message(exc)
