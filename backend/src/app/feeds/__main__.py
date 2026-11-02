"""Validate feeds.yaml and list its feeds: `uv run python -m app.feeds [path]`."""

import sys

from .loader import DEFAULT_FEEDS_PATH, FeedConfigError, load_feed_registry


def main(argv: list[str]) -> int:
    path = argv[1] if len(argv) > 1 else DEFAULT_FEEDS_PATH
    try:
        registry = load_feed_registry(path)
    except FeedConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for feed in registry.feeds:
        status = "active  " if feed.active else "inactive"
        print(
            f"{status}  {feed.id:<28} {feed.source_type.value:<11} {feed.category:<15} {feed.url}"
        )
    print(f"\n{len(registry.active())} active / {len(registry.feeds)} total feeds in {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
