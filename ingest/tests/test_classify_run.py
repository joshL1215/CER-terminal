from cer_db import Article, ArticleStatus
from sqlalchemy import select

from app.classify import classify_pending
from app.repository import NewArticle, insert_new_articles


def add_articles(session, *titles):
    insert_new_articles(
        session,
        [
            NewArticle("alpha", f"https://alpha.example.com/{n}", title)
            for n, title in enumerate(titles)
        ],
    )
    session.commit()


def statuses(session):
    session.expire_all()
    return {a.title: a for a in session.scalars(select(Article))}


def classify(factory, rules, providers, client, **kwargs):
    return classify_pending(factory, rules, providers, client, sleep=lambda _: None, **kwargs)


def test_all_answered(session, feeds, factory, rules, providers, fake_llm, llm_answer):
    add_articles(session, "Grid one", "Grid two")
    client = fake_llm(lambda provider, ids: llm_answer(ids, keep=True))

    stats = classify(factory, rules, providers, client)

    assert (stats.batches, stats.kept, stats.rejected, stats.unanswered) == (1, 2, 0, 0)
    rows = statuses(session)
    one = rows["Grid one"]
    assert one.status is ArticleStatus.KEPT
    assert one.category == "grid"
    assert one.model == "primary.example.com/model-a"
    assert one.rules_version == "test-v1"


def test_keyword_filter_skips_llm(session, feeds, factory, rules, providers, fake_llm, llm_answer):
    add_articles(session, "Big giveaway", "Grid news")
    client = fake_llm(lambda provider, ids: llm_answer(ids))

    classify(factory, rules, providers, client)

    rows = statuses(session)
    assert rows["Big giveaway"].status is ArticleStatus.REJECTED
    assert rows["Big giveaway"].model == "keyword-filter"
    assert rows["Big giveaway"].reason == 'keyword pre-filter: "giveaway"'
    (_, asked_ids) = client.calls[0]
    assert asked_ids == [rows["Grid news"].id]


def test_partial_answer_leaves_rest_pending(
    session, feeds, factory, rules, providers, fake_llm, llm_answer
):
    add_articles(session, "A", "B")
    client = fake_llm(lambda provider, ids: llm_answer(ids[:1], keep=False))

    stats = classify(factory, rules, providers, client)

    assert (stats.rejected, stats.unanswered) == (1, 1)
    rows = statuses(session)
    assert rows["A"].status is ArticleStatus.REJECTED
    assert rows["B"].status is ArticleStatus.PENDING
    assert rows["B"].classification_attempts == 1


def test_total_failure_tried_once_per_run_then_failed_after_max(
    session, feeds, factory, rules, providers, fake_llm
):
    add_articles(session, "A", "B", "C")

    def broken(provider, ids):
        raise ValueError("down")

    for _ in range(3):
        client = fake_llm(broken)
        stats = classify(factory, rules, providers, client, batch_size=2, max_attempts=3)
        # 2 batches; each article sent once per provider per run, never re-sent in the same run.
        assert stats.batches == 2
        assert len(client.calls) == 4

    assert stats.failed == 3
    assert {a.status for a in statuses(session).values()} == {ArticleStatus.FAILED}


def test_max_batches_limits_llm_calls(
    session, feeds, factory, rules, providers, fake_llm, llm_answer
):
    add_articles(session, "A", "B", "C", "D", "E")
    client = fake_llm(lambda provider, ids: llm_answer(ids))

    stats = classify(factory, rules, providers, client, batch_size=2, max_batches=2)

    assert stats.batches == 2 and stats.kept == 4
    assert statuses(session)["E"].status is ArticleStatus.PENDING


def test_nothing_pending(feeds, factory, rules, providers, fake_llm):
    client = fake_llm(lambda provider, ids: "")
    stats = classify(factory, rules, providers, client)
    assert stats.batches == 0 and client.calls == []
