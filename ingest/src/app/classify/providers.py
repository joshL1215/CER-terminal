"""LLM endpoints, configured entirely from environment variables.

Any OpenAI-compatible chat completions API works (Groq, Gemini, OpenRouter,
Mistral, OpenAI, a local Ollama, ...). Switching hosts is a config change:

    LLM_BASE_URL, LLM_MODEL, LLM_API_KEY                 primary (required)
    LLM_FALLBACK_BASE_URL, LLM_FALLBACK_MODEL,
    LLM_FALLBACK_API_KEY                                 used if the primary fails (optional)
    LLM_JSON_MODE / LLM_FALLBACK_JSON_MODE               "false" if the host rejects
                                                         response_format=json_object
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit


class ProviderConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Provider:
    base_url: str
    model: str
    api_key: str = field(repr=False)
    json_mode: bool = True

    @property
    def label(self) -> str:
        """Stored as articles.model, e.g. 'api.groq.com/openai/gpt-oss-120b'."""
        host = urlsplit(self.base_url).hostname or self.base_url
        return f"{host}/{self.model}"[:100]


def _flag(value: str | None) -> bool:
    return (value or "true").strip().lower() not in ("0", "false", "no", "off")


def _provider(env: Mapping[str, str], prefix: str) -> Provider | None:
    values = {
        key: (env.get(f"{prefix}_{key}") or "").strip() for key in ("BASE_URL", "MODEL", "API_KEY")
    }
    if not any(values.values()):
        return None
    missing = [f"{prefix}_{key}" for key, value in values.items() if not value]
    if missing:
        raise ProviderConfigError(f"incomplete LLM config, missing: {', '.join(missing)}")
    return Provider(
        base_url=values["BASE_URL"],
        model=values["MODEL"],
        api_key=values["API_KEY"],
        json_mode=_flag(env.get(f"{prefix}_JSON_MODE")),
    )


def providers_from_env(env: Mapping[str, str] = os.environ) -> list[Provider]:
    """Configured providers in the order to try them; empty if none are set."""
    return [
        provider
        for provider in (_provider(env, "LLM"), _provider(env, "LLM_FALLBACK"))
        if provider is not None
    ]
