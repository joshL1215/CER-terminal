import pytest

from app.classify import Provider, ProviderConfigError, providers_from_env

PRIMARY = {
    "LLM_BASE_URL": "https://api.groq.com/openai/v1",
    "LLM_MODEL": "openai/gpt-oss-120b",
    "LLM_API_KEY": "secret",
}


def test_no_config_means_no_providers():
    assert providers_from_env({}) == []


def test_primary_only():
    (provider,) = providers_from_env(PRIMARY)
    assert provider.model == "openai/gpt-oss-120b"
    assert provider.json_mode is True
    assert provider.label == "api.groq.com/openai/gpt-oss-120b"


def test_primary_and_fallback():
    env = PRIMARY | {
        "LLM_FALLBACK_BASE_URL": "https://other.example.com/v1",
        "LLM_FALLBACK_MODEL": "m2",
        "LLM_FALLBACK_API_KEY": "k2",
        "LLM_FALLBACK_JSON_MODE": "false",
    }
    primary, fallback = providers_from_env(env)
    assert primary.base_url == PRIMARY["LLM_BASE_URL"]
    assert (fallback.model, fallback.json_mode) == ("m2", False)


def test_partial_config_is_an_error():
    with pytest.raises(ProviderConfigError, match="LLM_API_KEY"):
        providers_from_env({"LLM_BASE_URL": "https://x", "LLM_MODEL": "m"})


def test_api_key_not_in_repr():
    assert "secret" not in repr(Provider("https://x", "m", "secret"))
