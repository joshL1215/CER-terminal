"""Load and validate the RSS feed registry from YAML.

Usage in the ingest loop:

    registry = load_feed_registry("config/feeds.yaml")
    for feed in registry.active():
        fetch(feed.url)  # feed.name, feed.category, feed.llm_context, ...
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .models import FeedDefaults, FeedRegistry

DEFAULT_FEEDS_PATH = Path(__file__).resolve().parents[3] / "config" / "feeds.yaml"


class FeedConfigError(ValueError):
    """Raised when feeds.yaml is missing, malformed, or fails validation."""


class _StrictSafeLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys.

    Plain PyYAML silently keeps the last value for a repeated key, which would
    hide copy-paste mistakes such as a feed with two `url:` lines.
    """


def _construct_mapping_no_duplicates(loader: _StrictSafeLoader, node: yaml.MappingNode) -> dict:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in mapping:
            line = key_node.start_mark.line + 1
            raise FeedConfigError(f"duplicate key {key!r} on line {line}")
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping_no_duplicates
)


def parse_feed_registry(text: str, source: str = "<string>") -> FeedRegistry:
    """Parse feeds.yaml content into a validated FeedRegistry."""
    try:
        raw = yaml.load(text, Loader=_StrictSafeLoader)
    except FeedConfigError as exc:
        raise FeedConfigError(f"{source}: {exc}") from None
    except yaml.YAMLError as exc:
        raise FeedConfigError(f"{source}: invalid YAML: {exc}") from None

    if not isinstance(raw, dict):
        raise FeedConfigError(f"{source}: top level must be a mapping with 'version' and 'feeds'")

    unknown = set(raw) - {"version", "defaults", "feeds"}
    if unknown:
        raise FeedConfigError(f"{source}: unknown top-level keys: {sorted(unknown)}")

    try:
        defaults = FeedDefaults.model_validate(raw.get("defaults") or {})
    except ValidationError as exc:
        raise FeedConfigError(f"{source}: invalid 'defaults':\n{_format_errors(exc)}") from None

    raw_feeds = raw.get("feeds")
    if not isinstance(raw_feeds, list) or not raw_feeds:
        raise FeedConfigError(f"{source}: 'feeds' must be a non-empty list")

    merged_feeds = []
    for index, entry in enumerate(raw_feeds):
        if not isinstance(entry, dict):
            raise FeedConfigError(f"{source}: feeds[{index}] must be a mapping")
        merged_feeds.append({**defaults.model_dump(), **entry})

    try:
        return FeedRegistry.model_validate({"version": raw.get("version"), "feeds": merged_feeds})
    except ValidationError as exc:
        raise FeedConfigError(f"{source}:\n{_format_errors(exc, merged_feeds)}") from None


def load_feed_registry(path: str | Path = DEFAULT_FEEDS_PATH) -> FeedRegistry:
    """Read and validate a feeds.yaml file."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FeedConfigError(f"could not read feed config {path}: {exc}") from None
    return parse_feed_registry(text, source=str(path))


def _format_errors(exc: ValidationError, feeds: list[dict] | None = None) -> str:
    """Turn pydantic errors into lines like `feeds[2] (utility-dive).url: ...`."""
    lines = []
    for error in exc.errors():
        loc = list(error["loc"])
        label = ""
        if feeds is not None and len(loc) >= 2 and loc[0] == "feeds" and isinstance(loc[1], int):
            index = loc[1]
            feed_id = feeds[index].get("id", "?") if index < len(feeds) else "?"
            label = f"feeds[{index}] ({feed_id})"
            loc = loc[2:]
        path = ".".join(str(part) for part in loc)
        prefix = f"{label}.{path}" if label and path else label or path or "document"
        lines.append(f"  - {prefix}: {error['msg']}")
    return "\n".join(lines)
