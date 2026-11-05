"""Call the configured LLMs with retries and fallback."""

import logging
import time
from collections.abc import Callable, Collection
from dataclasses import dataclass
from typing import Protocol

import openai

from .providers import Provider
from .response import Decision, ResponseParseError, parse_decisions

logger = logging.getLogger(__name__)

RETRYABLE_ERRORS = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.InternalServerError,
    ResponseParseError,
)


class ChatClient(Protocol):
    def complete(self, provider: Provider, messages: list[dict[str, str]]) -> str: ...


class OpenAICompatibleClient:
    """ChatClient for any OpenAI-compatible endpoint."""

    def __init__(self, timeout: float = 60.0):
        self._timeout = timeout
        self._clients: dict[Provider, openai.OpenAI] = {}

    def complete(self, provider: Provider, messages: list[dict[str, str]]) -> str:
        client = self._clients.get(provider)
        if client is None:
            client = openai.OpenAI(
                api_key=provider.api_key,
                base_url=provider.base_url,
                timeout=self._timeout,
                max_retries=0,
            )
            self._clients[provider] = client
        extra = {"response_format": {"type": "json_object"}} if provider.json_mode else {}
        response = client.chat.completions.create(
            model=provider.model, messages=messages, temperature=0, **extra
        )
        return response.choices[0].message.content or ""


class AllProvidersFailed(RuntimeError):
    pass


@dataclass(frozen=True)
class BatchOutcome:
    provider: Provider
    decisions: dict[int, Decision]


def decide(
    messages: list[dict[str, str]],
    expected_ids: Collection[int],
    categories: Collection[str],
    providers: list[Provider],
    client: ChatClient,
    *,
    attempts_per_provider: int = 2,
    backoff_seconds: float = 5.0,
    sleep: Callable[[float], None] = time.sleep,
) -> BatchOutcome:
    """Try each provider in order; retry rate limits, outages, and bad JSON with backoff."""
    for provider in providers:
        for attempt in range(1, attempts_per_provider + 1):
            try:
                text = client.complete(provider, messages)
                return BatchOutcome(provider, parse_decisions(text, expected_ids, categories))
            except RETRYABLE_ERRORS as exc:
                logger.warning("%s attempt %d failed: %s", provider.label, attempt, exc)
                if attempt < attempts_per_provider:
                    sleep(backoff_seconds * attempt)
            except Exception as exc:
                logger.warning("%s failed, not retrying: %s", provider.label, exc)
                break
    raise AllProvidersFailed("no LLM provider returned a usable answer")
