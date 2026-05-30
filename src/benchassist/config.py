"""Configuration module for BenchAssist-IL.

Loads settings from environment variables and .env file using python-dotenv.
Provides a cached settings instance via get_settings().
"""

from __future__ import annotations

import functools
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Resolve project root: walk upward until we find pyproject.toml or .git
# ---------------------------------------------------------------------------


def _find_project_root() -> Path:
    """Walk up from this file's directory to locate the project root."""
    current = Path(__file__).resolve().parent
    for ancestor in [current] + list(current.parents):
        if (ancestor / "pyproject.toml").exists() or (ancestor / ".git").exists():
            return ancestor
    # Fallback: two levels up from src/benchassist/
    return Path(__file__).resolve().parent.parent.parent


_PROJECT_ROOT = _find_project_root()

# Load .env from project root (if present)
load_dotenv(_PROJECT_ROOT / ".env")


def _parse_temperature(value: str | None) -> float:
    if value is None or value.strip() == "":
        return 0.0
    return float(value)


def _env_str(key: str, default: str) -> str:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    return raw.strip()


def _env_optional(key: str) -> Optional[str]:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return None
    return raw.strip()


# ---------------------------------------------------------------------------
# Settings dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Settings:
    """Application-wide configuration.

    Attributes:
        MODEL_PROVIDER: Backend identifier (``mock``, ``gemini``, or ``openai``).
        MODEL_NAME: Model name passed to the provider.
        GEMINI_API_KEY: Optional Google Gemini API key (env only).
        GOOGLE_API_KEY: Alternate env var accepted for Gemini API key.
        OPENAI_API_KEY: Optional OpenAI API key (env only).
        TEMPERATURE: Sampling temperature for generative models.
        LOG_LEVEL: Python logging level string.
        DATA_DIR: Root directory for raw / processed data artefacts.
        RESULTS_DIR: Root directory for pipeline outputs.
        PROMPTS_DIR: Directory containing prompt template files.
    """

    MODEL_PROVIDER: str = field(default="mock")
    MODEL_NAME: str = field(default="mock-benchassist")
    GEMINI_API_KEY: Optional[str] = field(default=None)
    GOOGLE_API_KEY: Optional[str] = field(default=None)
    OPENAI_API_KEY: Optional[str] = field(default=None)
    TEMPERATURE: float = field(default=0.0)
    LOG_LEVEL: str = field(default="INFO")
    DATA_DIR: Path = field(default_factory=lambda: _PROJECT_ROOT / "data")
    RESULTS_DIR: Path = field(default_factory=lambda: _PROJECT_ROOT / "results")
    PROMPTS_DIR: Path = field(default_factory=lambda: _PROJECT_ROOT / "prompts")


def resolve_gemini_api_key(settings: Settings | None = None) -> str | None:
    """Return a Gemini API key from ``GEMINI_API_KEY`` or ``GOOGLE_API_KEY``."""
    resolved = settings or get_settings()
    return resolved.GEMINI_API_KEY or resolved.GOOGLE_API_KEY


def _build_settings() -> Settings:
    """Build a ``Settings`` instance from environment variables."""
    return Settings(
        MODEL_PROVIDER=_env_str("MODEL_PROVIDER", "mock"),
        MODEL_NAME=_env_str("MODEL_NAME", "mock-benchassist"),
        GEMINI_API_KEY=_env_optional("GEMINI_API_KEY"),
        GOOGLE_API_KEY=_env_optional("GOOGLE_API_KEY"),
        OPENAI_API_KEY=_env_optional("OPENAI_API_KEY"),
        TEMPERATURE=_parse_temperature(os.getenv("TEMPERATURE")),
        LOG_LEVEL=_env_str("LOG_LEVEL", "INFO"),
        DATA_DIR=Path(os.getenv("DATA_DIR", str(_PROJECT_ROOT / "data"))),
        RESULTS_DIR=Path(os.getenv("RESULTS_DIR", str(_PROJECT_ROOT / "results"))),
        PROMPTS_DIR=Path(os.getenv("PROMPTS_DIR", str(_PROJECT_ROOT / "prompts"))),
    )


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached, read-only ``Settings`` instance.

    The instance is created on the first call and reused afterwards.
    To force re-creation (e.g. in tests), call
    ``get_settings.cache_clear()`` first.
    """
    return _build_settings()
