import httpx
from cer_db import Article, ArticleStatus
from sqlalchemy import select

from app.feeds import parse_feed_registry
from app.ingest import run_ingest
from app.ingest.__main__ import main
from app.repository import get_feed

REGISTRY = parse_feed_registry(
    """
    version: 1
    feeds:
      - {id: alpha, name: Alpha, url: 'https://alpha.example.com/rss'}
      - {id: down, name: Down, url: 'https://down.example.com/rss'}
      - {id: paused, name: Paused, url: 'https://paused.example.com/rss', active: false}
    """
)

RSS = b"""<rss version="2.0"><channel><title>Alpha</title>
<item><title>Grid story</title><link>https://alpha.example.com/grid</link></item>
<item><title>Huge giveaway</title><link>https://alpha.example.com/deal</link></item>
<item><title>Grid story again</title><link>https://alpha.example.com/grid/?utm_source=rss</link></item>
</channel></rss>"""


def make_transport(calls):
    def handler(request):
        calls.append(request.url.host)
        if request.url.host == "down.example.com":
            return httpx.Response(500)
        if request.headers.get("if-none-match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(200, content=RSS, headers={"ETag": '"v1"'})

    return httpx.MockTransport(handler)


def test_end_to_end(session, factory, rules, providers, fake_llm, llm_answer):
    calls = []
    client = fake_llm(lambda provider, ids: llm_answer(ids, keep=True))

    def ingest():
        return run_ingest(
            factory,
            REGISTRY,
            rules,
            providers=providers,
            chat_client=client,
            transport=make_transport(calls),
        )

    first = ingest()
    assert (first.feeds_ok, first.feeds_failed, first.new_articles) == (1, 1, 2)
    assert "down" in first.failed_feeds
    assert (first.classify.kept, first.classify.rejected) == (1, 1)
    assert "paused.example.com" not in calls

    articles = {a.title: a for a in session.scalars(select(Article))}
    assert articles["Grid story"].status is ArticleStatus.KEPT
    assert articles["Huge giveaway"].status is ArticleStatus.REJECTED
    assert get_feed(session, "alpha").etag == '"v1"'
    assert get_feed(session, "down").consecutive_failures == 1

    second = ingest()
    assert (second.feeds_not_modified, second.new_articles) == (1, 0)
    assert second.classify.batches == 0
    session.expire_all()
    assert get_feed(session, "alpha").etag == '"v1"'
    assert get_feed(session, "down").consecutive_failures == 2


def test_skip_classify_and_no_providers(session, factory, rules, fake_llm):
    client = fake_llm(lambda provider, ids: "")
    calls = []
    for kwargs in ({"classify": False, "providers": ["unused"]}, {"providers": []}):
        summary = run_ingest(
            factory, REGISTRY, rules, chat_client=client, transport=make_transport(calls), **kwargs
        )
        assert summary.classify is None
    assert client.calls == []
    assert {a.status for a in session.scalars(select(Article))} == {ArticleStatus.PENDING}


def test_main_config_errors_exit_2(monkeypatch, tmp_path):
    for name in ("DATABASE_URL", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert main(["--skip-classify"]) == 2

    bad = tmp_path / "rules.yaml"
    bad.write_text("version: v1\n")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    assert main(["--rules", str(bad)]) == 2

    monkeypatch.setenv("LLM_BASE_URL", "https://x.example.com")
    assert main([]) == 2  # incomplete LLM config


def test_main_database_error_exits_1(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'empty.db'}")  # no tables
    assert main(["--skip-classify"]) == 1
