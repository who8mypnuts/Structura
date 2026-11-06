"""ParamSpec: the single declaration of a setting (docs/02 §6.2). Export sheets, CLI flags, presets and
validation are all generated from these."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ParamType(Enum):
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    ENUM = "enum"
    STRING = "string"


@dataclass(frozen=True)
class ParamSpec:
    key: str
    type: ParamType
    default: Any
    label: str = ""
    doc: str = ""
    choices: tuple[str, ...] = ()
    range: tuple[float, float] | None = None

    @property
    def title(self) -> str:
        return self.label or self.key.replace("_", " ").capitalize()

    def coerce(self, value: Any) -> Any:
        """Convert text (CLI, presets) or loose values to the declared type; raise ValueError if invalid."""
        if self.type == ParamType.BOOL:
            return value if isinstance(value, bool) else str(value).strip().lower() in ("1", "true", "yes", "on")
        if self.type == ParamType.INT:
            return self._ranged(int(value))
        if self.type == ParamType.FLOAT:
            return self._ranged(float(value))
        if self.type == ParamType.ENUM:
            if str(value) not in self.choices:
                raise ValueError(f"{self.key}: expected one of {', '.join(self.choices)}, got {value!r}")
            return str(value)
        return str(value)

    def _ranged(self, value: float) -> Any:
        if self.range is not None and not self.range[0] <= value <= self.range[1]:
            raise ValueError(f"{self.key}: {value} is outside {self.range[0]}…{self.range[1]}")
        return value


def resolve(specs: tuple[ParamSpec, ...], given: dict[str, Any] | None = None) -> dict[str, Any]:
    """Defaults overlaid with ``given`` (coerced); unknown keys are an error."""
    values = {s.key: s.default for s in specs}
    by_key = {s.key: s for s in specs}
    for key, value in (given or {}).items():
        if key not in by_key:
            raise ValueError(f"unknown option '{key}' (known: {', '.join(sorted(by_key))})")
        values[key] = by_key[key].coerce(value)
    return values
