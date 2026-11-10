"""Semantic checks on a parsed script (docs/05 §10): unused and unreachable rules, v1 pitfalls, unbounded
recursion, obsolete settings and v2 material / settings resolution. Qt-free. Every check returns
diagnostics in *original* text positions; codes and severities come from catalog/diagnostics.toml."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from ..scene.declarations import SceneDeclarations
from ..scene.material import presets
from .ast import Action, CallAction, Program, SetAction
from .catalog import operator_names
from .diagnostics import Diagnostic, diagnostic
from .graph import TOP, call_graph, reachable, recursive_groups
from .highlight import lex_line
from .position_map import PositionMap
from .source import Span

LEGACY_CAMERA_KEYS = frozenset({"translation", "rotation", "pivot", "scale", "perspective-angle"})
_WORD = re.compile(r"[A-Za-z_]\w*")


@dataclass(frozen=True)
class LintInput:
    text: str  # the original script
    source: str  # the preprocessed text the parser saw (program spans refer to it)
    program: Program
    positions: PositionMap
    dialect: int
    defines: Mapping[str, str]
    declarations: SceneDeclarations | None

    def span(self, span: Span) -> Span:
        return self.positions.span(span) or span

    def header(self, span: Span) -> Span:
        """The 'rule NAME …' part of a definition (original text), up to its '{'."""
        original = self.span(span)
        brace = self.text.find("{", original.start, original.end)
        return Span(original.start, brace if brace > original.start else original.end)


def _actions(program: Program) -> Iterator[Action]:
    yield from program.top
    for rule in program.rules:
        yield from rule.body


def _calls(program: Program) -> Iterator[CallAction]:
    return (a for a in _actions(program) if isinstance(a, CallAction))


def _sets(program: Program) -> Iterator[SetAction]:
    return (a for a in _actions(program) if isinstance(a, SetAction))


ENUM_CHOICES = re.compile(r"^\s*#param\s+\w+\s+enum\b.*?\sof\s+(\S+)", re.MULTILINE)


def unused_and_unreachable(inp: LintInput) -> list[Diagnostic]:
    graph = call_graph(inp.program)
    choices = {c.lower() for m in ENUM_CHOICES.finditer(inp.text) for c in m.group(1).split("|")}
    graph[TOP] = {*graph.get(TOP, ()), *choices}  # a v2 enum parameter may name any of its rules
    referenced = {t for targets in graph.values() for t in targets}
    live = reachable(graph)
    out, seen = [], set()
    for rule in inp.program.rules:
        if rule.name in seen:
            continue
        seen.add(rule.name)
        if rule.name not in referenced:
            out.append(diagnostic("W101", f"rule '{rule.name}' is never referenced", inp.header(rule.span)))
        elif rule.name not in live:
            out.append(diagnostic("W102", f"rule '{rule.name}' is unreachable from the top level",
                                  inp.header(rule.span)))  # fmt: skip
    return out


def unbounded_recursion(inp: LintInput) -> list[Diagnostic]:
    if any(s.key == "maxdepth" for s in _sets(inp.program)):
        return []
    bounded = {r.name for r in inp.program.rules if r.maxdepth is not None}
    out = []
    for group in recursive_groups(call_graph(inp.program)):
        if group & bounded:
            continue
        first = next(r for r in inp.program.rules if r.name in group)
        names = ", ".join(sorted(group))
        out.append(diagnostic("W108", f"recursion through {names} is bounded only by the default maxdepth (1000)",
                              inp.header(first.span)))  # fmt: skip
    return out


def zero_weights(inp: LintInput) -> list[Diagnostic]:
    totals: dict[str, list[float]] = {}
    for rule in inp.program.rules:
        totals.setdefault(rule.name, []).append(rule.weight)
    out = []
    for name, weights in totals.items():
        if len(weights) > 1 and sum(weights) == 0:
            first = next(r for r in inp.program.rules if r.name == name)
            out.append(diagnostic("W110", f"ambiguous rule '{name}' has total weight 0", inp.header(first.span)))
    return out


def obsolete_settings(inp: LintInput) -> list[Diagnostic]:
    return [diagnostic("W109", "'set rng old' is obsolete: the Mersenne Twister is always used", inp.span(s.span))
            for s in _sets(inp.program) if s.key == "rng" and s.value == "old"]  # fmt: skip


def legacy_aliases(inp: LintInput) -> list[Diagnostic]:
    """W106: operator spellings Structure Synth 1.5 rejects ('size', 'v')."""
    names, out = operator_names(), []
    for call in _calls(inp.program):
        for loop in call.loops:
            for op in loop.ops:
                word = _WORD.match(inp.source, op.span.start)
                spelled = word.group(0) if word else op.name
                canonical, legacy = names.get(spelled, (op.name, True))
                if not legacy:
                    start = inp.span(Span(op.span.start, op.span.start + len(spelled)))
                    out.append(diagnostic("W106", f"'{spelled}' is not valid in Structure Synth 1.5; use "
                                          f"'{canonical}'", start))  # fmt: skip
    return out


def v1_cylinders(inp: LintInput) -> list[Diagnostic]:
    if inp.dialect != 1:
        return []
    message = "Structure Synth 1.5 did not draw cylinders (Structura does; 1.5 template exports omit them)"
    calls = (c for c in _calls(inp.program) if c.target.split("::")[0] == "cylinder")
    return [diagnostic("W105", message, inp.span(c.span)) for c in calls]


def _code_words(text: str) -> Iterator[tuple[int, str]]:
    """(offset, word) of identifiers outside comments and preprocessor lines."""
    offset, state = 0, 0
    for line in text.split("\n"):
        tokens, state = lex_line(line, state)
        for start, length, role in tokens:
            if role not in ("comment", "preprocessor"):  # words inside tokens too: 'triangle[0,0,off]'
                for word in _WORD.finditer(line, start, start + length):
                    yield offset + word.start(), word.group(0)
        offset += len(line) + 1


def define_substrings(text: str, dialect: int, defines: Mapping[str, str]) -> list[Diagnostic]:
    """W103 (v1): '#define R 5' also rewrites 'R1' and 'tree' in Structure Synth 1.5. Text-based, so it also
    explains the parse error such a substitution usually causes."""
    if dialect != 1 or not defines:
        return []
    out = []
    words = list(_code_words(text))
    for name in defines:
        hit = next(((at, w) for at, w in words if name in w and w != name and not w.startswith("#")), None)
        line = re.search(rf"(?m)^[ \t]*#define[ \t]+{re.escape(name)}\b.*$", text)
        if hit is not None and line is not None:
            message = (f"#define {name} also replaces text inside '{hit[1]}' (v1 substitutes substrings; "
                       "'#version 2' substitutes whole words)")  # fmt: skip
            out.append(diagnostic("W103", message, Span(line.start(), line.end())))
    return out


def _material_names(inp: LintInput) -> Iterator[tuple[str, Span]]:
    """Every material a v2 script asks for: tags ('box::shiny') and 'mat shiny' operators."""
    for call in _calls(inp.program):
        for loop in call.loops:
            yield from ((str(op.args[0]), op.span) for op in loop.ops if op.name == "mat")
        if tag := call.target.partition("::")[2]:
            yield tag, call.span


def material_resolution(inp: LintInput) -> list[Diagnostic]:
    """W112 / I203 (v2): tags and 'mat' names without a material block."""
    if inp.declarations is None:
        return []
    declared, builtin, out, seen = set(inp.declarations.materials), set(presets()), [], set()
    for name, span in _material_names(inp):
        if name in declared or name in seen:
            continue
        seen.add(name)
        if name in builtin:
            out.append(diagnostic("I203", f"'{name}' uses the built-in '{name}' material", inp.span(span)))
        else:
            out.append(diagnostic("W112", f"'{name}' has no material: the default is used", inp.span(span)))
    return out


def overridden_settings(inp: LintInput) -> list[Diagnostic]:
    """W113 (v2): camera / render blocks override 'set' lines."""
    decl = inp.declarations
    if decl is None:
        return []
    out = []
    for s in _sets(inp.program):
        if decl.camera and s.key in LEGACY_CAMERA_KEYS:
            out.append(diagnostic("W113", f"'set {s.key}' is overridden by the camera block", inp.span(s.span)))
        elif decl.render and s.key.startswith("raytracer::"):
            out.append(diagnostic("W113", f"'set {s.key}' is overridden by the render block", inp.span(s.span)))
    return out


CHECKS = (unused_and_unreachable, unbounded_recursion, zero_weights, obsolete_settings, legacy_aliases,
          v1_cylinders, material_resolution, overridden_settings)  # fmt: skip


def lint(inp: LintInput) -> list[Diagnostic]:
    return [d for check in CHECKS for d in check(inp)]
