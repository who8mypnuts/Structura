"""Exception hierarchy for the domain layer (docs/02-architecture.md §6.5)."""

from __future__ import annotations


class StructuraError(Exception):
    """Base class for all user-facing domain errors."""

    def __init__(self, message: str, hint: str = "", code: str = "E009") -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.code = code  # diagnostics catalogue (core/lang/catalog/diagnostics.toml)


class BuildError(StructuraError):
    """Raised when building a scene fails (bad set-command value, colour pool file missing, ...)."""


class UnresolvedRuleError(BuildError):
    """A call names no rule or primitive (diagnostic E003)."""

    def __init__(self, message: str, name: str) -> None:
        super().__init__(message, code="E003")
        self.name = name


class ColorError(StructuraError):
    """Raised for an unparseable colour specification."""
