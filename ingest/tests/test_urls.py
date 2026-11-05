import pytest

from app.urls import canonicalize_url, url_hash


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://Example.com/a/b/", "https://example.com/a/b"),
        ("HTTPS://example.com:443/a", "https://example.com/a"),
        ("http://example.com:80/a", "http://example.com/a"),
        ("https://example.com:8443/a", "https://example.com:8443/a"),
        ("https://example.com/a#section", "https://example.com/a"),
        ("https://example.com", "https://example.com/"),
        ("https://example.com/a?b=2&a=1", "https://example.com/a?a=1&b=2"),
        ("https://example.com/a?utm_source=x&id=5&fbclid=y", "https://example.com/a?id=5"),
        ("  https://example.com/a  ", "https://example.com/a"),
    ],
)
def test_canonicalize_url(url, expected):
    assert canonicalize_url(url) == expected


def test_url_hash_matches_for_equivalent_urls():
    assert url_hash("https://example.com/story?utm_medium=rss") == url_hash(
        "https://EXAMPLE.com/story/"
    )
    assert url_hash("https://example.com/a") != url_hash("https://example.com/b")
    assert len(url_hash("https://example.com/a")) == 64


def test_path_case_is_preserved():
    # Paths can be case-sensitive on the server, so don't fold them.
    assert url_hash("https://example.com/Story") != url_hash("https://example.com/story")
