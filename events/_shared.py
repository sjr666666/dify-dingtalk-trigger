"""Shared helpers for DingTalk trigger event handlers."""

from __future__ import annotations

from typing import Any, Mapping


def pick(data: Mapping[str, Any], *names: str, default: Any = "") -> Any:
    """Return the first non-empty value among ``names`` (case variants).

    DingTalk mixes snake_case keys (new events) and PascalCase keys (legacy
    events) across its event catalogue, so handlers accept both spellings.
    """
    for name in names:
        value = data.get(name)
        if value is not None and value != "":
            return value
    return default


def as_str(value: Any) -> str:
    """Coerce a scalar payload value to a plain string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)
