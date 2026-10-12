import os
import time
from typing import Type, TypeVar
from pathlib import Path
from pydantic import BaseModel
from dotenv import dotenv_values, load_dotenv

# Load environment variables from common local configuration locations.
load_dotenv()
current_dir = Path(__file__).resolve().parent
for parent in [current_dir.parent.parent, current_dir.parent.parent.parent]:
    env_file = parent / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)

try:
    from google import genai
    from google.genai import types, errors
except ImportError:
    genai = None
    types = None
    errors = None

T = TypeVar("T", bound=BaseModel)
BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class GeminiMissingKeyError(Exception):
    """Raised when GEMINI_API_KEY is not set or contains default placeholder."""
    pass


class GeminiAPIError(Exception):
    """Raised when a Gemini provider or network error occurs."""
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_api_key() -> str:
    """Safely retrieves and validates the Gemini API key from environment."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "your_gemini_api_key_here":
        file_key = str(dotenv_values(BACKEND_ENV_FILE).get("GEMINI_API_KEY", "")).strip()
        if file_key and file_key != "your_gemini_api_key_here":
            key = file_key

    if not key or key == "your_gemini_api_key_here":
        raise GeminiMissingKeyError(
            "Gemini API key is not configured. Please add 'GEMINI_API_KEY=your_actual_key' "
            "to your backend/.env file or Windows environment variables. "
            "The backend reads backend/.env when an agent request is made."
        )
    return key


def get_model_name() -> str:
    """Returns configured model name or default recommended model."""
    return os.getenv("GEMINI_MODEL", "").strip() or "gemini-3.8-flash"


def generate_structured(prompt: str, schema_cls: Type[T], system_instruction: str = "") -> T:
    """
    Executes a structured generation request against the Gemini API using Google Gen AI SDK.
    Validates and returns the response as an instance of schema_cls.
    """
    if genai is None:
        raise GeminiAPIError("google-genai SDK is not installed.", status_code=500)

    api_key = get_api_key()
    model = get_model_name()

    try:
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema_cls,
            system_instruction=system_instruction if system_instruction else None,
            temperature=0.2,
        )

        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )
                break
            except errors.APIError as e:
                if getattr(e, "code", None) != 503 or attempt == 1:
                    raise
                time.sleep(1)

        if not response or not response.text:
            raise GeminiAPIError("Model returned an empty response.", status_code=502)

        return schema_cls.model_validate_json(response.text)

    except GeminiMissingKeyError:
        raise
    except errors.APIError as e:
        status_code = getattr(e, "code", 502) or 502
        if status_code == 429:
            raise GeminiAPIError(
                "Gemini API rate limit or quota exceeded. Please wait a moment or check your quota in Google AI Studio.",
                status_code=429
            )
        elif status_code in (401, 403):
            raise GeminiAPIError(
                "Gemini API key is invalid or unauthorized. Please verify your GEMINI_API_KEY in .env.",
                status_code=401
            )
        elif status_code == 404:
            raise GeminiAPIError(
                f"Gemini model '{model}' is unavailable to this API key. "
                "Update GEMINI_MODEL in backend/.env to a model listed by Google AI Studio.",
                status_code=404
            )
        elif status_code == 503:
            raise GeminiAPIError(
                "Gemini is temporarily overloaded. Please wait a moment and try again.",
                status_code=503
            )
        else:
            raise GeminiAPIError(f"Gemini API error: {str(e)}", status_code=502)
    except Exception as e:
        raise GeminiAPIError(f"Gemini execution error: {str(e)}", status_code=502)
