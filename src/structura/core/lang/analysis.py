"""Editor-facing analysis of a script (docs/12 §5): diagnostics and symbols in *original* text positions.

One call runs the whole v1 front end. A successful analysis carries the compiled program, so a live build
can start without compiling again.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path

from ..errors import StructuraError, UnresolvedRuleError
from .ast import CallAction, Loop, Program, RuleDef
from .compile.program import RuleProgram, compile_rule_set
from .diagnostics import Diagnostic, ParseError, Severity, diagnostic
from .inlay import Hint, inlay_hints
from .legacy.gui_params import apply_gui_parameters
from .legacy.parser import parse_legacy
from .legacy.preprocessor import GuiParameter, LegacyPreprocessor, PreprocessResult
from .lint import LintInput, define_substrings, lint
from .position_map import PositionMap
from .resolve import build_rule_set
from .source import Span, is_javascript
from .v2.front import Front, after_preprocessing, front, timeline_names, v2_syntax


@dataclass(frozen=True)
class RuleSymbol:
    name: str
    span: Span  # the whole definition
    weight: float
    maxdepth: int | None


@dataclass(frozen=True)
class Analysis:
    version: int
    diagnostics: tuple[Diagnostic, ...]
    rules: tuple[RuleSymbol, ...] = ()
    references: Mapping[str, tuple[Span, ...]] = field(default_factory=dict)
    parameters: tuple[GuiParameter, ...] = ()
    program: RuleProgram | None = None
    positions: PositionMap | None = None
    digest: str = ""  # hash of the preprocessed source: equal digests build identical scenes
    hints: tuple[Hint, ...] = ()  # inlay hints (probabilities, loop counts, materials)
    defines: tuple[str, ...] = ()  # '#define' names (the editor colours their uses as substitutions)

    def semantic_symbols(self) -> tuple[frozenset[str] | None, frozenset[str], frozenset[str]]:
        """(defined rules or None before a successful parse, unused rules, define names) for highlighting."""
        parsed = bool(self.rules) or self.program is not None
        defined = frozenset(r.name for r in self.rules) if parsed else None
        unused = frozenset(r.name for r in self.rules if r.name not in self.references)
        return defined, unused, frozenset(self.defines)

    @property
    def ok(self) -> bool:
        return self.program is not None and not any(d.severity == Severity.ERROR for d in self.diagnostics)

    def action_at(self, position: int) -> int | None:
        """The compiled action (call site) whose original span contains ``position``: the innermost one."""
        if self.program is None or self.positions is None:
            return None
        best: tuple[int, int] | None = None
        for action, span in enumerate(self.program.action_spans):
            original = self.positions.span(span)
            if original is not None and original.start <= position <= original.end:
                width = original.end - original.start
                if best is None or width < best[1]:
                    best = (action, width)
        return best[0] if best else None

    def action_span(self, action: int) -> Span | None:
        """Original-text span of a compiled action (SceneIR.source provenance)."""
        if self.program is None or self.positions is None or not 0 <= action < len(self.program.action_spans):
            return None
        return self.positions.span(self.program.action_spans[action])


def _calls(actions: tuple[object, ...]) -> list[CallAction]:
    return [a for a in actions if isinstance(a, CallAction)]


def _symbols(program: Program, pm: PositionMap) -> tuple[tuple[RuleSymbol, ...], dict[str, tuple[Span, ...]]]:
    rules = tuple(RuleSymbol(r.name, pm.span(r.span) or r.span, r.weight, r.maxdepth) for r in program.rules)
    refs: dict[str, list[Span]] = {}
    bodies: list[tuple[object, ...]] = [program.top, *(r.body for r in program.rules)]
    for body in bodies:
        for call in _calls(body):
            span = pm.span(call.span) or call.span
            refs.setdefault(call.target.split("::")[0], []).append(span)
    for rule in program.rules:  # 'rule A maxdepth 3 > B' references B
        if rule.retirement:
            refs.setdefault(rule.retirement, []).append(pm.span(rule.span) or rule.span)
    return rules, {k: tuple(v) for k, v in refs.items()}


def _front_diagnostics(text: str, fr: Front, pre: PreprocessResult) -> list[Diagnostic]:
    """Checks that need no parse: v2 block errors, preprocessor warnings (spans in the front text), v1
    define substitutions inside words, and the v2-syntax hint."""
    front_map = PositionMap(text, fr.text)
    out = [*fr.diagnostics, *(replace(d, span=front_map.span(d.span)) for d in pre.diagnostics)]
    out += define_substrings(text, 2 if fr.v2 else 1, pre.defines)
    hint = v2_syntax(text)
    if hint is not None:
        out.append(diagnostic("W114", "v2 syntax needs '#version 2' on the first line", hint))
    return out


def analyze(
    text: str,
    seed: int = 0,
    params: Mapping[str, float] | None = None,
    script_dir: Path | None = None,
    version: int = 0,
    frame: int = 0,
    fps: float = 24.0,
) -> Analysis:
    """``frame`` and ``fps`` bind the v2 animation variables (the timeline's current frame)."""
    if is_javascript(text):
        message = "JavaScript script: run it with Build ▸ Run JavaScript (F7)"
        return Analysis(version, (diagnostic("I204", message, Span(0, len(text.partition("\n")[0]))),))
    fr = front(text)
    pre = LegacyPreprocessor(fr.v2).process(fr.text, seed)
    substituted = apply_gui_parameters(pre.text, pre.parameters, params, fr.v2)
    names = tuple(sorted({*pre.defines, *(p.name for p in pre.parameters)}))  # plain defines and sliders
    diagnostics = _front_diagnostics(text, fr, pre)
    try:
        source = after_preprocessing(substituted, fr, timeline_names(frame, fps))
    except ParseError as exc:  # expression errors are positioned in the text before evaluation
        error = Diagnostic(exc.code, Severity.ERROR, exc.message, PositionMap(text, substituted).span(exc.span))
        return Analysis(version, (*diagnostics, error), parameters=tuple(pre.parameters), defines=names)
    pm = PositionMap(text, source)  # parser spans refer to the text after v2 expressions were evaluated
    try:
        parsed = parse_legacy(source, fr.v2)
    except ParseError as exc:
        error = Diagnostic(exc.code, Severity.ERROR, exc.message, pm.span(exc.span))
        return Analysis(version, (*diagnostics, error), parameters=tuple(pre.parameters), defines=names)
    rules, refs = _symbols(parsed, pm)
    hints = inlay_hints(parsed, pm, fr.declarations)
    dialect = 2 if fr.v2 else 1
    diagnostics += lint(LintInput(text, source, parsed, pm, dialect, pre.defines, fr.declarations))
    try:
        program = replace(compile_rule_set(build_rule_set(parsed, fr.v2), script_dir), declarations=fr.declarations)
    except (ParseError, StructuraError) as exc:
        span = pm.span(getattr(exc, "span", None))
        if isinstance(exc, UnresolvedRuleError) and exc.name in refs:
            span = refs[exc.name][0]
        error = Diagnostic(getattr(exc, "code", "E009"), Severity.ERROR, exc.message, span)
        return Analysis(version, (*diagnostics, error), rules, refs, tuple(pre.parameters), hints=hints,
                        defines=names)  # fmt: skip
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()
    return Analysis(version, tuple(diagnostics), rules, refs, tuple(pre.parameters), program, pm, digest, hints,
                    names)  # fmt: skip


__all__ = ["Analysis", "Loop", "RuleDef", "RuleSymbol", "analyze"]
