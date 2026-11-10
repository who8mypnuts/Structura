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

from ...color import parse_color
from ...rng import mt_get_double, mt_new
from ..diagnostics import Diagnostic, Severity
from ..source import Span

_DEFINE_FLOAT = re.compile(r"^#define\s([^\s]+)\s(.*)\s\(float:([^\s]*)\)$")
_DEFINE_INT = re.compile(r"^#define\s([^\s]+)\s(.*)\s\(int:([^\s]*)\)$")
_DEFINE = re.compile(r"^#define\s([^\s]+)\s(.*)$")
_DEFINE_TYPED = re.compile(r"^#define\s([^\s]+)\s(\S+)\s\((color|bool|enum)(?::([^\s)]*))?\)$")  # v2 #param
_RANDOM = re.compile(r"random\[([-+]?[0-9]*\.?[0-9]+),([-+]?[0-9]*\.?[0-9]+)\]")
_RAND_V2 = re.compile(r"(?<![\w.])rand\(\s*([-+]?[0-9]*\.?[0-9]+)\s*,\s*([-+]?[0-9]*\.?[0-9]+)\s*\)")  # docs/05 §9.1
_LINE_SPLIT = re.compile(r"\r\n|\r|\n")
_KNOWN = re.compile(r"\s*#(version|javascript)\b", re.IGNORECASE)
MAX_SUBSTITUTIONS = 100


@dataclass(frozen=True, slots=True)
class GuiParameter:
    name: str
    kind: str  # "float" | "int"; v2 #param adds "color" (0xRRGGBB), "bool" (0 / 1), "enum" (a choice's index)
    minimum: float
    maximum: float
    default: float
    line: int  # 0-based source line
    choices: tuple[str, ...] = ()  # enum: the names, substituted for the index

    @property
    def numeric(self) -> bool:
        """A slider parameter (float or int), as opposed to a colour, switch or choice."""
        return self.kind in ("float", "int")


@dataclass
class PreprocessResult:
    text: str
    parameters: list[GuiParameter] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)  # spans are in the *input* text
    defines: dict[str, str] = field(default_factory=dict)


def typed_parameter(name: str, kind: str, default: str, extra: str, line: int) -> GuiParameter | None:
    """A colour, switch or choice parameter; None when the default does not fit."""
    if kind == "bool":
        return GuiParameter(name, kind, 0.0, 1.0, 1.0 if default == "true" else 0.0, line)
    if kind == "enum":
        choices = tuple(c for c in extra.split("|") if c)
        if default not in choices:
            return None
        return GuiParameter(name, kind, 0.0, float(len(choices) - 1), float(choices.index(default)), line, choices)
    colour = parse_color(default)
    if colour is None:
        return None
    packed = (round(colour.r / 257) << 16) | (round(colour.g / 257) << 8) | round(colour.b / 257)
    return GuiParameter(name, kind, 0.0, float(0xFFFFFF), float(packed), line)


def format_number(value: float) -> str:
    """Number formatting used when substituting values into script text (6 significant digits)."""
    return f"{value:g}"


def _word(name: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])")


def substitute(
    text: str, table: dict[str, str], limit: int = MAX_SUBSTITUTIONS, whole_words: bool = False
) -> tuple[str, bool]:
    """Substitution in sorted key order, restarting after every hit. Returns (text, capped).

    Structure Synth 1.5 replaces raw substrings ('#define R 5' also rewrites 'R1'); v2 scripts replace whole
    words only (``whole_words``)."""
    keys = sorted(table)
    hits, k = 0, 0
    while k < len(keys):
        if hits > limit:
            return text, True
        pattern = _word(keys[k]) if whole_words else None
        found = pattern.search(text) if pattern else keys[k] in text
        if found:
            value = table[keys[k]]
            text = pattern.sub(value.replace("\\", "\\\\"), text) if pattern else text.replace(keys[k], value)
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

    def __init__(self, whole_words: bool = False) -> None:
        self.whole_words = whole_words  # '#version 2': defines replace whole words, not substrings
        self.result = PreprocessResult("")
        self.substitutions: dict[str, str] = {}
        self._line = Span(0, 0)  # the line being processed, for diagnostic positions

    def warn(self, code: str, message: str) -> None:
        self.result.diagnostics.append(Diagnostic(code, Severity.WARNING, message, self._line))

    def process(self, text: str, seed: int = 0) -> PreprocessResult:
        rng = mt_new(seed)
        lines = _LINE_SPLIT.split(text)
        starts = [0] + [m.end() for m in _LINE_SPLIT.finditer(text)]
        for index, raw in enumerate(lines):
            self._line = Span(starts[index], starts[index] + len(raw))
            if raw.startswith("#"):
                self._directive(raw, index)
                line = raw
            else:
                line = self._apply_defines(raw)
                if self.whole_words:  # v2: 'rand(a, b)' in an expression is 'random[a,b]' (the same stream)
                    line = _RAND_V2.sub(r"random[\1,\2]", line)
            lines[index] = self._replace_random(line, rng)
        self.result.text = "\r\n".join(lines)
        self.result.defines = dict(self.substitutions)
        return self.result

    def _apply_defines(self, line: str) -> str:
        line, capped = substitute(line, self.substitutions, whole_words=self.whole_words)
        if capped:
            self.warn("W104", "More than 100 recursive preprocessor substitutions... breaking.")
        return line

    def _directive(self, line: str, index: int) -> None:
        if _KNOWN.match(line):
            return  # '#version 2' (handled by the v2 front end) and '#javascript' (a script, not EisenScript)
        typed = _DEFINE_TYPED.match(line) if self.whole_words else None
        if typed:
            self._typed_parameter(typed, index)
            return
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

    def _typed_parameter(self, match: re.Match[str], index: int) -> None:
        """'#define NAME DEFAULT (color)', '(bool)' or '(enum:a|b|c)' — what v2's #param becomes."""
        name, default, kind, extra = match.group(1), match.group(2), match.group(3), match.group(4) or ""
        param = typed_parameter(name, kind, default, extra, index)
        if param is None:
            self.warn("W121", f"Could not parse #param: {match.group(0)}")
            return
        self.result.parameters.append(param)

    @staticmethod
    def _replace_random(line: str, rng: np.ndarray) -> str:
        while True:
            match = _RANDOM.search(line)
            if not match:
                return line
            low, high = float(match.group(1)), float(match.group(2))
            value = mt_get_double(rng) * (high - low) + low
            line = line.replace(match.group(0), format_number(value))
