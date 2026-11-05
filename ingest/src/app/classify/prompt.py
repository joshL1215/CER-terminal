import json
from dataclasses import asdict, dataclass

from app.rules import RelevanceRules


@dataclass(frozen=True)
class ArticleInput:
    """What the LLM sees about one article."""

    id: int
    title: str
    description: str | None
    source: str
    source_category: str
    source_context: str | None


def _bullets(items: tuple[str, ...]) -> str:
    return "\n".join(f"- {item}" for item in items) or "- (none)"


RESPONSE_SHAPE = (
    '{"results": [{"id": <article id>, "keep": true or false, '
    '"category": "<allowed category>" or null, "reason": "<one short sentence>"}]}'
)


def build_messages(rules: RelevanceRules, articles: list[ArticleInput]) -> list[dict[str, str]]:
    system = f"""You screen news articles for an energy research center's news feed.
Decide for each article whether to keep it.

Keep articles about:
{_bullets(rules.keep)}

Reject articles about:
{_bullets(rules.reject)}

Allowed categories: {", ".join(rules.categories)}

Each article includes its source and, sometimes, notes about that source; use them as context.
Respond with only a JSON object of this shape, with one result per article id:
{RESPONSE_SHAPE}"""

    payload = [{key: value for key, value in asdict(a).items() if value} for a in articles]
    user = "Articles:\n" + json.dumps(payload, ensure_ascii=False, indent=1)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
