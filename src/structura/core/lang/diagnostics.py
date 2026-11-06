"""Diagnostics produced by the language front end (codes: docs/05 §10)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .source import Span


class Severity(IntEnum):
    HINT = 0
    INFO = 1
    WARNING = 2
    ERROR = 3


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    span: Span | None = None


class ParseError(Exception):
    """A fatal parse error (legacy-strict mode stops at the first one, like Structure Synth 1.5)."""

    def __init__(self, message: str, span: Span | None, code: str = "E001") -> None:
        super().__init__(message)
        self.message = message
        self.span = span
        self.code = code

    def diagnostic(self) -> Diagnostic:
        return Diagnostic(self.code, Severity.ERROR, self.message, self.span)
