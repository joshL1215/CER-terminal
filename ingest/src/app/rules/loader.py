from pathlib import Path

import yaml
from pydantic import ValidationError

from app.strict_yaml import DuplicateKeyError, load_strict_yaml

from .models import RelevanceRules

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[3] / "config" / "rules.yaml"


class RulesConfigError(ValueError):
    """Raised when rules.yaml is missing, malformed, or fails validation."""


def parse_rules(text: str, source: str = "<string>") -> RelevanceRules:
    try:
        raw = load_strict_yaml(text)
    except DuplicateKeyError as exc:
        raise RulesConfigError(f"{source}: {exc}") from None
    except yaml.YAMLError as exc:
        raise RulesConfigError(f"{source}: invalid YAML: {exc}") from None

    if not isinstance(raw, dict):
        raise RulesConfigError(f"{source}: top level must be a mapping")
    try:
        return RelevanceRules.model_validate(raw)
    except ValidationError as exc:
        lines = [
            f"  - {'.'.join(str(part) for part in error['loc']) or 'document'}: {error['msg']}"
            for error in exc.errors()
        ]
        raise RulesConfigError(f"{source}:\n" + "\n".join(lines)) from None


def load_rules(path: str | Path = DEFAULT_RULES_PATH) -> RelevanceRules:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RulesConfigError(f"could not read rules config {path}: {exc}") from None
    return parse_rules(text, source=str(path))
