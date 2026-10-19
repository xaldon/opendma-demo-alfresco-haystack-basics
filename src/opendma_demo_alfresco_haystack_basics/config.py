"""Configuration helpers for the sample applications."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings read from environment variables."""

    endpoint: str
    username: str
    password: str
    repository_id: str
    chat_model: str
    embedding_model: str


def load_settings() -> Settings:
    """Load settings with defaults matching the local tutorial setup."""
    return Settings(
        endpoint=os.environ.get("OPENDMA_ALFRESCO_ENDPOINT", "http://localhost:7070/opendma/alf"),
        username=os.environ.get("ALFRESCO_USERNAME", "admin"),
        password=os.environ.get("ALFRESCO_PASSWORD", "admin"),
        repository_id=os.environ.get("ALFRESCO_REPOSITORY_ID", "Alfresco"),
        chat_model=os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        embedding_model=os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
    )


def require_openai_api_key() -> None:
    """Fail early for commands that need OpenAI calls."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY must be set for this command.")

