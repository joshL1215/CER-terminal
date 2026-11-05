import pytest

from app.rules import RulesConfigError, load_rules, parse_rules


def test_bundled_rules_are_valid():
    rules = load_rules()
    assert rules.version
    assert "grid" in rules.categories
    assert rules.keep and rules.reject


def test_rules_are_normalized():
    rules = parse_rules(
        """
        version: 3
        categories: [Grid, policy]
        keep: ["  Grid   news ", ""]
        keyword_reject: [Giveaway, giveaway]
        """
    )
    assert rules.version == "3"
    assert rules.categories == ("grid", "policy")
    assert rules.keep == ("Grid news",)
    assert rules.keyword_reject == ("giveaway",)


def test_keyword_match(rules):
    assert rules.keyword_match("Huge GIVEAWAY today") == "giveaway"
    assert rules.keyword_match("Grid update") is None


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("categories: [grid]", "version"),
        ("version: v1", "categories"),
        ("version: v1\ncategories: []", "categories"),
        ("version: v1\ncategories: [Bad Category]", "lowercase slug"),
        ("version: v1\ncategories: [grid, grid]", "unique"),
        ("version: v1\ncategories: [grid]\nkepp: [x]", "kepp"),
        ("version: v1\nversion: v2\ncategories: [grid]", "duplicate key"),
        ("- a list", "mapping"),
        ("version: [", "invalid YAML"),
    ],
)
def test_invalid_rules(body, message):
    with pytest.raises(RulesConfigError, match=message):
        parse_rules(body)


def test_missing_rules_file():
    with pytest.raises(RulesConfigError, match="could not read"):
        load_rules("/nonexistent/rules.yaml")
