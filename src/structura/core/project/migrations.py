"""Project-file migrations (docs/07 §8): each entry upgrades a raw JSON object from version N to N + 1.
A new format version adds one function here; loading runs the chain up to the current version."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

CURRENT_VERSION = 1
Migration = Callable[[dict[str, Any]], dict[str, Any]]
MIGRATIONS: dict[int, Migration] = {}  # version -> function producing version + 1


class NewerProjectError(ValueError):
    """The file was written by a newer Structura."""


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    version = int(data.get("format_version", 1))
    if version > CURRENT_VERSION:
        raise NewerProjectError(f"project format {version} is newer than this Structura ({CURRENT_VERSION})")
    while version < CURRENT_VERSION:
        data = MIGRATIONS[version](data)
        version += 1
        data["format_version"] = version
    return data
