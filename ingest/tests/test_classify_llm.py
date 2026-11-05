import httpx
import openai
import pytest

from app.classify import AllProvidersFailed, decide

MESSAGES = [{"role": "system", "content": "s"}, {"role": "user", "content": "Articles:\n[]"}]


def status_error(cls, code):
    request = httpx.Request("POST", "https://llm.example.com/v1/chat/completions")
    return cls("error", response=httpx.Response(code, request=request), body=None)


class ScriptedClient:
    """Returns or raises the next scripted item for each call."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls = []

    def complete(self, provider, messages):
        self.calls.append(provider.model)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


OK = '{"results": [{"id": 1, "keep": true, "category": "grid", "reason": "x"}]}'


def run(client, providers, sleeps=None):
    sleep = sleeps.append if sleeps is not None else (lambda _: None)
    return decide(MESSAGES, [1], ["grid"], providers, client, sleep=sleep)


def test_first_provider_success(providers):
    client = ScriptedClient(OK)
    outcome = run(client, providers)
    assert outcome.provider is providers[0]
    assert outcome.decisions[1].keep
    assert client.calls == ["model-a"]


def test_rate_limit_retries_with_backoff_then_falls_back(providers):
    client = ScriptedClient(
        status_error(openai.RateLimitError, 429),
        status_error(openai.RateLimitError, 429),
        OK,
    )
    sleeps = []
    outcome = run(client, providers, sleeps)
    assert outcome.provider is providers[1]
    assert client.calls == ["model-a", "model-a", "model-b"]
    assert sleeps == [5.0]


def test_malformed_json_is_retried(providers):
    client = ScriptedClient("not json", OK)
    outcome = run(client, providers)
    assert outcome.provider is providers[0]
    assert client.calls == ["model-a", "model-a"]


def test_non_retryable_error_skips_to_fallback(providers):
    client = ScriptedClient(status_error(openai.AuthenticationError, 401), OK)
    outcome = run(client, providers)
    assert outcome.provider is providers[1]
    assert client.calls == ["model-a", "model-b"]


def test_all_providers_fail(providers):
    client = ScriptedClient(
        status_error(openai.InternalServerError, 500),
        status_error(openai.InternalServerError, 503),
        ValueError("unexpected"),
    )
    with pytest.raises(AllProvidersFailed):
        run(client, providers)
    assert client.calls == ["model-a", "model-a", "model-b"]
