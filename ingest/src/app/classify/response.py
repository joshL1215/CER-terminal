"""Validate the LLM's JSON answer."""

import json
import re
from collections.abc import Collection

from pydantic import BaseModel, ValidationError

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")
MAX_REASON_LENGTH = 500


class ResponseParseError(ValueError):
    pass


class Decision(BaseModel):
    id: int
    keep: bool
    category: str | None = None
    reason: str = ""


class _Response(BaseModel):
    results: list[Decision]


def parse_decisions(
    text: str, expected_ids: Collection[int], categories: Collection[str]
) -> dict[int, Decision]:
    """Decisions keyed by article id; ids the LLM skipped are simply absent.

    Unknown ids are ignored, and categories outside the allowed list become None.
    """
    cleaned = _FENCE.sub("", text.strip())
    try:
        response = _Response.model_validate(json.loads(cleaned))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ResponseParseError(f"invalid LLM response: {exc}") from None

    expected = set(expected_ids)
    decisions: dict[int, Decision] = {}
    for decision in response.results:
        if decision.id not in expected or decision.id in decisions:
            continue
        category = (decision.category or "").strip().lower()
        decisions[decision.id] = decision.model_copy(
            update={
                "category": category if category in categories else None,
                "reason": " ".join(decision.reason.split())[:MAX_REASON_LENGTH],
            }
        )
    return decisions
