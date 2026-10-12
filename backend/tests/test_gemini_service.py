from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from google.genai import errors
from pydantic import BaseModel

from app.services import gemini_service


class ExampleResponse(BaseModel):
    result: str


def _api_error(status_code: int) -> errors.APIError:
    return errors.APIError(status_code, {"message": "temporarily unavailable"})


def _configure_client(monkeypatch, generate_content):
    models = SimpleNamespace(generate_content=generate_content)
    client = SimpleNamespace(models=models)
    monkeypatch.setattr(
        gemini_service,
        "genai",
        SimpleNamespace(Client=Mock(return_value=client)),
    )
    monkeypatch.setattr(
        gemini_service,
        "types",
        SimpleNamespace(GenerateContentConfig=lambda **kwargs: kwargs),
    )
    monkeypatch.setattr(gemini_service, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(gemini_service.time, "sleep", lambda _seconds: None)


def test_generate_structured_retries_once_after_gemini_503(monkeypatch):
    generate_content = Mock(
        side_effect=[
            _api_error(503),
            SimpleNamespace(text='{"result":"ok"}'),
        ]
    )
    _configure_client(monkeypatch, generate_content)

    result = gemini_service.generate_structured("prompt", ExampleResponse)

    assert result == ExampleResponse(result="ok")
    assert generate_content.call_count == 2


def test_generate_structured_reports_gemini_503_after_retry(monkeypatch):
    generate_content = Mock(side_effect=_api_error(503))
    _configure_client(monkeypatch, generate_content)

    with pytest.raises(gemini_service.GeminiAPIError) as exc_info:
        gemini_service.generate_structured("prompt", ExampleResponse)

    assert exc_info.value.status_code == 503
    assert "temporarily overloaded" in str(exc_info.value)
    assert generate_content.call_count == 2
