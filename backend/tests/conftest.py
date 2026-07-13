"""Shared test isolation for SOSFlow backend tests."""

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def disable_real_bedrock_calls(monkeypatch):
    """Unit/API tests never consume AWS credentials or paid model invocations.

    Bedrock-specific tests construct an explicit Settings object and fake
    Converse client, while the separate verification script is responsible for
    proving a real configured Bedrock invocation.
    """
    monkeypatch.setattr(get_settings(), "ai_provider", "mock")
