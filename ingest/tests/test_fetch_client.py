import asyncio

import httpx

from app.fetch import FeedRequest, FetchStatus, fetch_all
from app.fetch.client import USER_AGENT

RSS = b"""<rss version="2.0"><channel><title>x</title>
<item><title>Story</title><link>https://example.com/story</link></item>
</channel></rss>"""


def run(requests, handler):
    return asyncio.run(fetch_all(requests, transport=httpx.MockTransport(handler)))


def test_ok_feed_returns_articles_and_cache_headers():
    seen = {}

    def handler(request):
        seen["ua"] = request.headers["user-agent"]
        return httpx.Response(200, content=RSS, headers={"ETag": '"v2"', "Last-Modified": "Tue"})

    (result,) = run([FeedRequest("a", "https://a.example.com/rss")], handler)
    assert result.status is FetchStatus.OK
    assert [a.title for a in result.articles] == ["Story"]
    assert (result.etag, result.last_modified) == ('"v2"', "Tue")
    assert seen["ua"] == USER_AGENT
    assert "@" not in USER_AGENT


def test_conditional_get_and_304_keeps_existing_headers():
    def handler(request):
        assert request.headers["if-none-match"] == '"v1"'
        assert request.headers["if-modified-since"] == "Mon"
        return httpx.Response(304)

    (result,) = run([FeedRequest("a", "https://a.example.com/rss", '"v1"', "Mon")], handler)
    assert result.status is FetchStatus.NOT_MODIFIED
    assert (result.etag, result.last_modified) == ('"v1"', "Mon")
    assert result.articles == []


def test_no_conditional_headers_without_stored_state():
    def handler(request):
        assert "if-none-match" not in request.headers
        assert "if-modified-since" not in request.headers
        return httpx.Response(200, content=RSS)

    (result,) = run([FeedRequest("a", "https://a.example.com/rss")], handler)
    assert result.status is FetchStatus.OK
    assert result.etag is None


def test_one_failing_feed_does_not_affect_others():
    def handler(request):
        host = request.url.host
        if host == "down.example.com":
            raise httpx.ConnectError("connection refused")
        if host == "forbidden.example.com":
            return httpx.Response(403)
        if host == "html.example.com":
            return httpx.Response(200, content=b"<html>not a feed</html")
        return httpx.Response(200, content=RSS)

    requests = [
        FeedRequest(name, f"https://{name}.example.com/rss")
        for name in ("down", "forbidden", "html", "good")
    ]
    results = {r.request.feed_id: r for r in run(requests, handler)}
    assert results["good"].status is FetchStatus.OK
    assert results["down"].status is FetchStatus.FAILED
    assert "ConnectError" in results["down"].error
    assert results["forbidden"].error == "HTTP 403"
    assert results["html"].status is FetchStatus.FAILED


def test_unexpected_error_is_isolated():
    def handler(request):
        if request.url.host == "boom.example.com":
            raise RuntimeError("bug")
        return httpx.Response(200, content=RSS)

    requests = [
        FeedRequest("boom", "https://boom.example.com/rss"),
        FeedRequest("ok", "https://ok.example.com/rss"),
    ]
    results = {r.request.feed_id: r for r in run(requests, handler)}
    assert results["boom"].status is FetchStatus.FAILED
    assert results["ok"].status is FetchStatus.OK
