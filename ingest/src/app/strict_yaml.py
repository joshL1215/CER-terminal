"""YAML loading that rejects duplicate keys.

Plain PyYAML silently keeps the last value for a repeated key, which would hide
copy-paste mistakes such as a feed with two `url:` lines.
"""

from typing import Any

import yaml


class DuplicateKeyError(ValueError):
    pass


class _StrictSafeLoader(yaml.SafeLoader):
    pass


def _construct_mapping_no_duplicates(loader: _StrictSafeLoader, node: yaml.MappingNode) -> dict:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in mapping:
            line = key_node.start_mark.line + 1
            raise DuplicateKeyError(f"duplicate key {key!r} on line {line}")
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping_no_duplicates
)


def load_strict_yaml(text: str) -> Any:
    """Parse YAML safely; raises DuplicateKeyError or yaml.YAMLError."""
    return yaml.load(text, Loader=_StrictSafeLoader)
