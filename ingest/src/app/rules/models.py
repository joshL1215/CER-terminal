import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

CATEGORY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _clean_list(values: list[str]) -> list[str]:
    cleaned = [" ".join(str(value).split()) for value in values]
    return [value for value in cleaned if value]


class RelevanceRules(BaseModel):
    """The contents of config/rules.yaml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = Field(min_length=1, max_length=64)
    categories: tuple[str, ...] = Field(min_length=1)
    keep: tuple[str, ...] = ()
    reject: tuple[str, ...] = ()
    keyword_reject: tuple[str, ...] = ()

    @field_validator("version", mode="before")
    @classmethod
    def _version_to_str(cls, value: object) -> object:
        return str(value).strip() if isinstance(value, (str, int, float)) else value

    @field_validator("categories", mode="before")
    @classmethod
    def _check_categories(cls, value: object) -> object:
        if not isinstance(value, (list, tuple)):
            return value
        categories = [str(item).strip().lower() for item in value]
        for category in categories:
            if not CATEGORY_PATTERN.fullmatch(category) or len(category) > 64:
                raise ValueError(f"category {category!r} must be a lowercase slug (max 64 chars)")
        if len(set(categories)) != len(categories):
            raise ValueError("categories must be unique")
        return tuple(categories)

    @field_validator("keep", "reject", mode="before")
    @classmethod
    def _clean_guidance(cls, value: object) -> object:
        return tuple(_clean_list(value)) if isinstance(value, (list, tuple)) else value

    @field_validator("keyword_reject", mode="before")
    @classmethod
    def _clean_keywords(cls, value: object) -> object:
        if not isinstance(value, (list, tuple)):
            return value
        return tuple(dict.fromkeys(keyword.lower() for keyword in _clean_list(value)))

    def keyword_match(self, title: str) -> str | None:
        """The first keyword_reject phrase found in the title, if any."""
        lowered = title.lower()
        return next((keyword for keyword in self.keyword_reject if keyword in lowered), None)
