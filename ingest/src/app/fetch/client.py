"""Download feeds concurrently, using conditional GET so unchanged feeds are cheap."""

import asyncio
from dataclasses import dataclass, field
from enum import StrEnum

import httpx

from app.repository import NewArticle

from .parse import FeedParseError, parse_entries

USER_AGENT = "CER-Energy-Terminal/0.1 (+https://github.com/joshL1215/CER-terminal)"
DEFAULT_TIMEOUT = 15.0
DEFAULT_CONCURRENCY = 10


class FetchStatus(StrEnum):
    OK = "ok"
    NOT_MODIFIED = "not_modified"
    FAILED = "failed"


@dataclass(frozen=True)
class FeedRequest:
    feed_id: str
    url: str
    etag: str | None = None
    last_modified: str | None = None


@dataclass
class FetchResult:
    request: FeedRequest
    status: FetchStatus
    articles: list[NewArticle] = field(default_factory=list)
    etag: str | None = None
    last_modified: str | None = None
    error: str | None = None


async def fetch_feed(client: httpx.AsyncClient, request: FeedRequest) -> FetchResult:
    headers = {}
    if request.etag:
        headers["If-None-Match"] = request.etag
    if request.last_modified:
        headers["If-Modified-Since"] = request.last_modified

    try:
        response = await client.get(request.url, headers=headers)
    except httpx.HTTPError as exc:
        return FetchResult(request, FetchStatus.FAILED, error=f"{type(exc).__name__}: {exc}")

    if response.status_code == 304:
        return FetchResult(
            request,
            FetchStatus.NOT_MODIFIED,
            etag=request.etag,
            last_modified=request.last_modified,
        )
    if response.status_code >= 400:
        return FetchResult(request, FetchStatus.FAILED, error=f"HTTP {response.status_code}")

    try:
        articles = parse_entries(request.feed_id, response.content)
    except FeedParseError as exc:
        return FetchResult(request, FetchStatus.FAILED, error=str(exc))
    return FetchResult(
        request,
        FetchStatus.OK,
        articles=articles,
        etag=response.headers.get("etag"),
        last_modified=response.headers.get("last-modified"),
    )


async def fetch_all(
    requests: list[FeedRequest],
    *,
    concurrency: int = DEFAULT_CONCURRENCY,
    timeout: float = DEFAULT_TIMEOUT,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[FetchResult]:
    """Fetch every feed; one feed failing never affects the others."""
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
        follow_redirects=True,
        transport=transport,
    ) as client:

        async def guarded(request: FeedRequest) -> FetchResult:
            async with semaphore:
                try:
                    return await fetch_feed(client, request)
                except Exception as exc:
                    return FetchResult(
                        request, FetchStatus.FAILED, error=f"{type(exc).__name__}: {exc}"
                    )

        return list(await asyncio.gather(*(guarded(request) for request in requests)))
