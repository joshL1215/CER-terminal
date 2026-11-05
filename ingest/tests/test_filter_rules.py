"""Sample article decisions and configuration errors; no database fixtures needed."""

import pytest

from app.filtering.rules import (
    FilterConfigError,
    RuleDecision,
    filter_article,
    load_filter_rules,
    parse_filter_rules,
)


@pytest.fixture
def rules():
    # Behavioral tests use fixed rules so editing the live config cannot change
    # their meaning. Exclusions remain covered even when disabled in production.
    return parse_filter_rules(
        """
version: 1
topics:
  oil: [oil]
  gas: [natural gas]
  coal: [coal]
  evs: [electric vehicle]
  renewables: [solar, wind energy]
  grid: [battery storage]
exclusions: [phone accessories, test drive, discount code]
"""
    )


def test_bundled_filter_rules_are_valid():
    assert load_filter_rules().topics


@pytest.mark.parametrize("exclusions", ["", "exclusions: []"])
def test_exclusions_can_be_omitted_or_empty(exclusions):
    rules = parse_filter_rules(f"version: 1\ntopics: {{evs: [electric vehicle]}}\n{exclusions}")
    result = filter_article("Electric vehicle review: a new test drive", None, rules)
    assert result.decision is RuleDecision.NEEDS_REVIEW
    assert result.matched_exclusions == ()
    result = filter_article("Best phone accessories this holiday season", None, rules)
    assert result.decision is RuleDecision.IRRELEVANT


@pytest.mark.parametrize(
    ("title", "decision", "topics"),
    [
        (
            "Coal consumption falls as solar generation increases",
            RuleDecision.NEEDS_REVIEW,
            ("coal", "renewables"),
        ),
        (
            "Best phone accessories this holiday season",
            RuleDecision.IRRELEVANT,
            (),
        ),
        (
            "Government announces new industrial policy",
            RuleDecision.IRRELEVANT,
            (),
        ),
        (
            "Electric vehicle review: a new test drive",
            RuleDecision.NEEDS_REVIEW,
            ("evs",),
        ),
    ],
)
def test_sample_articles(rules, title, decision, topics):
    result = filter_article(title, None, rules)
    assert result.decision is decision
    assert result.topics == topics
    assert result.reason


def test_description_can_supply_the_topic(rules):
    result = filter_article("New infrastructure investment", "Expands battery storage.", rules)
    assert result.decision is RuleDecision.NEEDS_REVIEW
    assert result.topics == ("grid",)
    assert result.matched_keywords == ("battery storage",)


def test_conflicts_across_fields_preserve_both_kinds_of_evidence(rules):
    result = filter_article("Solar generation expands", "Includes a discount code.", rules)
    assert result.decision is RuleDecision.NEEDS_REVIEW
    assert result.matched_keywords == ("solar",)
    assert result.matched_exclusions == ("discount code",)


@pytest.mark.parametrize("title", ["Soil quality improves", "Dev tools and medieval art", ""])
def test_substrings_and_empty_text_do_not_pass_the_filter(rules, title):
    result = filter_article(title, None, rules)
    assert result.decision is RuleDecision.IRRELEVANT
    assert result.matched_keywords == ()


def test_case_html_entities_hyphens_and_whitespace(rules):
    result = filter_article(
        "SOLAR-powered growth",
        "<p>NATURAL&nbsp;<b>GAS</b> and wind-\nenergy</p>",
        rules,
    )
    assert result.decision is RuleDecision.NEEDS_REVIEW
    assert result.topics == ("gas", "renewables")
    assert result.matched_keywords == ("natural gas", "solar", "wind energy")


def test_phrases_do_not_span_title_and_description(rules):
    result = filter_article("Natural", "Gas", rules)
    assert result.decision is RuleDecision.IRRELEVANT


def test_repeated_keywords_are_reported_once(rules):
    result = filter_article("Coal, coal, COAL", "Coal", rules)
    assert result.matched_keywords == ("coal",)


def test_custom_rules_and_literal_punctuation():
    rules = parse_filter_rules(
        """
version: 1
topics:
  heat:
    - Heat Pump
    - ' heat-pump '
  buildings:
    - heat pump
exclusions: [buy now]
"""
    )
    result = filter_article("Heat-pump adoption grows", None, rules)
    assert result.decision is RuleDecision.NEEDS_REVIEW
    assert result.topics == ("heat", "buildings")
    assert result.matched_keywords == ("heat pump",)
    assert filter_article("Solar adoption grows", None, rules).decision is RuleDecision.IRRELEVANT
    assert filter_article("Buy now!", None, rules).decision is RuleDecision.IRRELEVANT


@pytest.mark.parametrize(
    "body",
    [
        "",
        "- not a mapping",
        "version: 2\ntopics: {coal: [coal]}",
        "version: true\ntopics: {coal: [coal]}",
        "version: 1\ntopics: {}",
        "version: 1\ntopics: {coal: []}",
        "version: 1\ntopics: {coal: coal}",
        "version: 1\ntopics: {Coal: [coal]}",
        "version: 1\ntopics: {coal: [42]}",
        "version: 1\ntopics: {coal: ['  ']}",
        "version: 1\ntopics: {coal: ['.*']}",
        "version: 1\ntopics: {coal: [coal]}\nexclusions: coupon",
        "version: 1\ntopics: {coal: [coal]}\nexclusions: ['']",
        "version: 1\ntopics: {coal: [coal]}\nexclude: [coupon]",
        "version: 1\ntopics: [",
        "version: 1\nversion: 1\ntopics: {coal: [coal]}",
        "version: 1\ntopics: {coal: [coal], coal: [oil]}",
        "version: 1\ntopics: {coal: [coal]}\n? [bad, key]\n: value",
    ],
)
def test_invalid_rules_report_the_source(body):
    with pytest.raises(FilterConfigError, match="sample.yaml: invalid filter rules"):
        parse_filter_rules(body, source="sample.yaml")


def test_load_custom_file(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text("version: 1\ntopics: {nuclear: [nuclear]}", encoding="utf-8")
    rules = load_filter_rules(path)
    assert filter_article("Nuclear capacity expands", None, rules).topics == ("nuclear",)


def test_missing_rules_file(tmp_path):
    with pytest.raises(FilterConfigError, match="could not read filter rules"):
        load_filter_rules(tmp_path / "missing.yaml")


def test_rules_file_must_be_utf8(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_bytes(b"\xff")
    with pytest.raises(FilterConfigError, match="could not read filter rules"):
        load_filter_rules(path)
