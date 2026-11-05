"""Keyword prefiltering; no database, network calls, or model credentials required."""

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from html.parser import HTMLParser
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[3] / "config" / "filter_rules.yaml"


class FilterConfigError(ValueError):
    """Missing, malformed, or invalid filtering configuration."""


def _normalize(value: str) -> str:
    # Treat punctuation (including hyphens) as word separators, not regex syntax.
    return " ".join(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", value).casefold()))


def _normalize_keywords(values: list[str]) -> list[str]:
    keywords = [_normalize(value) for value in values]
    if any(not keyword for keyword in keywords):
        raise ValueError("keywords must contain at least one letter or number")
    return list(dict.fromkeys(keywords))


class FilterRules(BaseModel):
    """Versioned topic keywords and exclusions; all entries are literal phrases."""

    model_config = ConfigDict(extra="forbid", strict=True)

    version: int
    topics: dict[str, list[str]] = Field(min_length=1)
    exclusions: list[str] = Field(default_factory=list)

    @field_validator("version")
    @classmethod
    def _check_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("unsupported rules version; expected 1")
        return value

    @field_validator("topics")
    @classmethod
    def _check_topics(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        result = {}
        for topic, keywords in value.items():
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", topic):
                raise ValueError(f"topic {topic!r} must be a lowercase slug, e.g. 'natural-gas'")
            if not keywords:
                raise ValueError(f"topic {topic!r} must have at least one keyword")
            result[topic] = _normalize_keywords(keywords)
        return result

    @field_validator("exclusions")
    @classmethod
    def _check_exclusions(cls, value: list[str]) -> list[str]:
        return _normalize_keywords(value)


class _UniqueKeyLoader(yaml.SafeLoader):
    """Reject YAML typos that would otherwise silently replace earlier rules."""


def _construct_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode) -> dict:
    loader.flatten_mapping(node)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str):
            raise FilterConfigError("mapping keys must be strings")
        if key in mapping:
            raise FilterConfigError(f"duplicate key {key!r} on line {key_node.start_mark.line + 1}")
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def parse_filter_rules(text: str, source: str = "<string>") -> FilterRules:
    """Validate YAML rules and include their source in configuration errors."""
    try:
        raw = yaml.load(text, Loader=_UniqueKeyLoader)
        return FilterRules.model_validate(raw)
    except (yaml.YAMLError, ValidationError, FilterConfigError) as exc:
        raise FilterConfigError(f"{source}: invalid filter rules: {exc}") from None


def load_filter_rules(path: str | Path = DEFAULT_RULES_PATH) -> FilterRules:
    """Load rules once, then reuse them across articles."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise FilterConfigError(f"could not read filter rules {path}: {exc}") from None
    return parse_filter_rules(text, source=str(path))


class RuleDecision(StrEnum):
    IRRELEVANT = "irrelevant"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class RuleResult:
    """A heuristic decision and its evidence, separate from database article status."""

    decision: RuleDecision
    topics: tuple[str, ...]
    matched_keywords: tuple[str, ...]
    matched_exclusions: tuple[str, ...]
    reason: str


class _ArticleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _article_words(value: str) -> str:
    parser = _ArticleText()
    parser.feed(value)
    parser.close()
    return f" {_normalize(' '.join(parser.parts))} "


def filter_article(title: str, description: str | None, rules: FilterRules) -> RuleResult:
    """Match whole words/phrases in either field, ignoring case, HTML, and punctuation.

    At least one topic keyword in the title or description is required for human
    or AI review; articles without topic matches are irrelevant to this filter.
    Matching keywords does not verify research relevance or approve publication.
    """
    fields = (_article_words(title), _article_words(description or ""))

    def matches(keyword: str) -> bool:
        return any(f" {keyword} " in field for field in fields)

    topics = []
    keywords = []
    for topic, candidates in rules.topics.items():
        hits = [keyword for keyword in candidates if matches(keyword)]
        if hits:
            topics.append(topic)
            keywords.extend(hits)
    exclusions = tuple(keyword for keyword in rules.exclusions if matches(keyword))

    if topics and exclusions:
        decision = RuleDecision.NEEDS_REVIEW
        reason = "Both topic keywords and exclusions matched; review conflicting evidence."
    elif topics:
        decision = RuleDecision.NEEDS_REVIEW
        reason = "Topic keywords matched; review is needed to confirm research relevance."
    elif exclusions:
        decision = RuleDecision.IRRELEVANT
        reason = "Exclusions matched with no topic keywords."
    else:
        decision = RuleDecision.IRRELEVANT
        reason = "No topic keywords matched in the title or description."

    return RuleResult(
        decision=decision,
        topics=tuple(topics),
        matched_keywords=tuple(dict.fromkeys(keywords)),
        matched_exclusions=exclusions,
        reason=reason,
    )
