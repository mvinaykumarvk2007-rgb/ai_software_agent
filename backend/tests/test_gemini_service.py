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


def test_generate_structured_falls_back_after_gemini_503(monkeypatch):
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
    assert generate_content.call_args_list[0].kwargs["model"] == "gemini-3.8-flash"
    assert generate_content.call_args_list[1].kwargs["model"] == "gemini-2.5-flash"


def test_generate_structured_reports_error_when_fallback_is_overloaded(monkeypatch):
    generate_content = Mock(side_effect=_api_error(503))
    _configure_client(monkeypatch, generate_content)

    with pytest.raises(gemini_service.GeminiAPIError) as exc_info:
        gemini_service.generate_structured("prompt", ExampleResponse)

    assert exc_info.value.status_code == 503
    assert "primary and fallback models are temporarily overloaded" in str(exc_info.value)
    assert generate_content.call_count == 2
