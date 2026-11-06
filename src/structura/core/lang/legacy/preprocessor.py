"""EisenScript v1 preprocessor (docs/05-eisenscript-language.md §2).

Line-based: '#define NAME VALUE' adds a raw *substring* substitution (applied to later non-'#' lines, keys in
sorted order, restarting after each hit, at most 100 hits per line); '#define NAME DEFAULT (float:A-B)' and
'(int:A-B)' declare GUI parameters; 'random[a,b]' is replaced by a uniform number from a dedicated MT19937
stream seeded with the build seed (identical texts on one line share one draw). Lines keep their count and
order, and are re-joined with CR LF.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from ...rng import mt_get_double, mt_new
from ..diagnostics import Diagnostic, Severity

_DEFINE_FLOAT = re.compile(r"^#define\s([^\s]+)\s(.*)\s\(float:([^\s]*)\)$")
_DEFINE_INT = re.compile(r"^#define\s([^\s]+)\s(.*)\s\(int:([^\s]*)\)$")
_DEFINE = re.compile(r"^#define\s([^\s]+)\s(.*)$")
_RANDOM = re.compile(r"random\[([-+]?[0-9]*\.?[0-9]+),([-+]?[0-9]*\.?[0-9]+)\]")
_LINE_SPLIT = re.compile(r"\r\n|\r|\n")
MAX_SUBSTITUTIONS = 100


@dataclass(frozen=True, slots=True)
class GuiParameter:
    name: str
    kind: str  # "float" | "int"
    minimum: float
    maximum: float
    default: float
    line: int  # 0-based source line


@dataclass
class PreprocessResult:
    text: str
    parameters: list[GuiParameter] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def format_number(value: float) -> str:
    """Number formatting used when substituting values into script text (6 significant digits)."""
    return f"{value:g}"


def substitute(text: str, table: dict[str, str], limit: int = MAX_SUBSTITUTIONS) -> tuple[str, bool]:
    """Raw substring substitution in sorted key order, restarting after every hit. Returns (text, capped)."""
    keys = sorted(table)
    hits, k = 0, 0
    while k < len(keys):
        if hits > limit:
            return text, True
        if keys[k] in text:
            text = text.replace(keys[k], table[keys[k]])
            hits += 1
            k = 0
        else:
            k += 1
    return text, False


def _to_float(text: str) -> float | None:
    try:
        return float(text.strip())
    except ValueError:
        return None


def _to_int(text: str) -> int | None:
    stripped = text.strip()
    return int(stripped) if re.fullmatch(r"[+-]?\d+", stripped) else None


class LegacyPreprocessor:
    """Stateless apart from a single run; create one per build."""

    def __init__(self) -> None:
        self.result = PreprocessResult("")
        self.substitutions: dict[str, str] = {}

    def warn(self, code: str, message: str) -> None:
        self.result.diagnostics.append(Diagnostic(code, Severity.WARNING, message))

    def process(self, text: str, seed: int = 0) -> PreprocessResult:
        rng = mt_new(seed)
        lines = _LINE_SPLIT.split(text)
        for index, raw in enumerate(lines):
            if raw.startswith("#"):
                self._directive(raw, index)
                line = raw
            else:
                line = self._apply_defines(raw)
            lines[index] = self._replace_random(line, rng)
        self.result.text = "\r\n".join(lines)
        return self.result

    def _apply_defines(self, line: str) -> str:
        line, capped = substitute(line, self.substitutions)
        if capped:
            self.warn("W104", "More than 100 recursive preprocessor substitutions... breaking.")
        return line

    def _directive(self, line: str, index: int) -> None:
        for pattern, kind in ((_DEFINE_FLOAT, "float"), (_DEFINE_INT, "int")):
            match = pattern.match(line)
            if match:
                self._gui_parameter(match, kind, index)
                return
        match = _DEFINE.match(line)
        if match:
            name, value = match.group(1), match.group(2)
            if name in value:
                self.warn("W104", f"#define command is recursive - skipped: {name} -> {value}")
            self.substitutions[name] = value  # Structure Synth applies it anyway (bounded by the cap)
            return
        self.warn("W120", f"Could not understand preprocessor command: {line}")

    def _gui_parameter(self, match: re.Match[str], kind: str, index: int) -> None:
        name, default_text, interval = match.group(1), match.group(2), match.group(3)
        if name in default_text:
            self.warn("W104", f"#define command is recursive - skipped: {name} -> {default_text}")
        convert = _to_float if kind == "float" else _to_int
        bounds = interval.split("-")
        if len(bounds) != 2:
            self.warn("W121", f"Could not understand #define gui command: {interval}")
            return
        low, high, default = convert(bounds[0]), convert(bounds[1]), convert(default_text)
        if low is None or high is None or default is None:
            self.warn("W121", f"Could not parse #define gui command: {match.group(0)}")
            return
        self.result.parameters.append(GuiParameter(name, kind, low, high, default, index))

    @staticmethod
    def _replace_random(line: str, rng: np.ndarray) -> str:
        while True:
            match = _RANDOM.search(line)
            if not match:
                return line
            low, high = float(match.group(1)), float(match.group(2))
            value = mt_get_double(rng) * (high - low) + low
            line = line.replace(match.group(0), format_number(value))
