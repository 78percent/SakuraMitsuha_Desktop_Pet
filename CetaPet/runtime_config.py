"""Read and update only this project's .env; never print secret values."""
from pathlib import Path

from dotenv import dotenv_values, set_key

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_MODEL = "deepseek-flash"


def _values():
    # Disable interpolation: a key must never expand another environment value.
    return dotenv_values(ENV_PATH, encoding="utf-8-sig", interpolate=False)


def read_api_key():
    return (_values().get("DEEPSEEK_API_KEY") or "").strip()


def read_model():
    return (_values().get("DEEPSEEK_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def save_api_key(key):
    key = key.strip()
    if not key or any(character in key for character in "\r\n\x00"):
        raise ValueError("API key must be a nonempty single line")
    set_key(ENV_PATH, "DEEPSEEK_API_KEY", key, quote_mode="always", encoding="utf-8")
