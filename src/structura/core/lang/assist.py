"""Completion and hover for the editor (docs/12 §3, §2.2). Qt-free; contexts come from the line lexer.

``complete(text, pos, analysis)`` returns the items valid at the cursor with the partial word they replace;
``hover(text, pos, analysis)`` returns Markdown-ish documentation for the word under the cursor.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from ..color.names import NAMED_COLORS
from .analysis import Analysis
from .catalog import (
    PrimitiveSpec,
    all_primitives,
    modifiers,
    operators,
    raytracer_keys,
    set_commands,
    snippets,
    v2_blocks,
)
from .highlight import lex_line
from .signatures import CONSTANTS, SIGNATURES
from .snippet_syntax import plain
from .source import detect_dialect
from .v2.blocks import enclosing_block

WORD = re.compile(r"[A-Za-z0-9_:#.\-]*$")
HEAD = re.compile(r"^[A-Za-z0-9_:#.\-]*")
COLOR_WORDS = ("color", "c", "blend", "background")


@dataclass(frozen=True)
class CompletionItem:
    label: str
    kind: str  # keyword | operator | modifier | primitive | rule | color | set | raytracer | snippet | preprocessor
    detail: str = ""
    doc: str = ""
    insert: str = ""  # defaults to the label

    @property
    def text(self) -> str:
        return self.insert or self.label


@dataclass(frozen=True)
class Completions:
    items: tuple[CompletionItem, ...]
    start: int  # document position where the replaced partial word begins
    prefix: str


def _ops() -> list[CompletionItem]:
    return [CompletionItem(o.name, "operator", " ".join(f"‹{a}›" for a in o.args), o.doc) for o in operators()]


def _prim_signature(p: PrimitiveSpec) -> str:
    return f"{p.name}[{p.param:g}] (v2)" if p.param is not None else ("primitive (v2)" if p.v2 else "primitive")


def _statements(analysis: Analysis | None) -> list[CompletionItem]:
    items = [
        CompletionItem("rule", "keyword", "rule NAME { … }", "Define a rule.", "rule "),
        CompletionItem("set", "keyword", "set KEY VALUE", "Change a build or render setting.", "set "),
    ]
    items += [CompletionItem(p.name, "primitive", _prim_signature(p), p.doc) for p in all_primitives()]
    items.append(CompletionItem("triangle", "primitive", "triangle[x,y,z;x,y,z;x,y,z]", "A triangle.", "triangle["))
    items += [CompletionItem(s.title, "snippet", s.group, plain(s.text), s.text) for s in snippets()
              if s.group == "Patterns"]  # fmt: skip
    return items + _rules(analysis)


def _rules(analysis: Analysis | None) -> list[CompletionItem]:
    if analysis is None:
        return []
    names = dict.fromkeys(r.name for r in analysis.rules)
    return [CompletionItem(n, "rule", "rule", f"Rule defined in this script ({_alternatives(analysis, n)}).")
            for n in names]  # fmt: skip


def _alternatives(analysis: Analysis, name: str) -> str:
    count = sum(1 for r in analysis.rules if r.name == name)
    return "1 definition" if count == 1 else f"{count} weighted alternatives"


def _set_keys() -> list[CompletionItem]:
    items = [CompletionItem(s.key, "set", s.value, s.doc) for s in set_commands()]
    return [*items, CompletionItem("raytracer::", "set", "raytracer settings", "Internal raytracer settings.")]


def _context(line: str) -> str:
    """Which completion list applies at the end of ``line`` (the text before the cursor, word removed)."""
    words = line.split()
    last = words[-1].lower() if words else ""
    rules = (
        (last == "set" and line.endswith(" "), "set"),
        (len(words) >= 2 and words[-2].lower() == "rule", "rule-modifier"),
        (last == ">", "rule"),
        (last in COLOR_WORDS, "color"),
        (line.count("{") > line.count("}"), "operator"),
    )
    return next((context for matched, context in rules if matched), "statement")


def _colors() -> list[CompletionItem]:
    named = [CompletionItem(n, "color", "#{:02x}{:02x}{:02x}".format(*rgb)) for n, rgb in NAMED_COLORS.items()]
    return [*named, CompletionItem("random", "color", "colour pool", "A colour drawn from the colour pool.")]


def _raytracer() -> list[CompletionItem]:
    return [CompletionItem(f"raytracer::{k.name}", "raytracer", k.value, k.doc) for k in raytracer_keys()]


def _block_keys(block: str) -> list[CompletionItem]:
    spec = v2_blocks().get(block)
    return [CompletionItem(k.name, "set", k.value, k.doc, k.name + " ") for k in spec.keys] if spec else []


def _functions() -> list[CompletionItem]:
    items = [CompletionItem(n, "function", f"{n}({', '.join(p)})", d, n + "(") for n, (p, d) in SIGNATURES.items()]
    return [*items, *(CompletionItem(n, "constant", "constant", d) for n, d in CONSTANTS.items())]


def _v2_statements(analysis: Analysis | None) -> list[CompletionItem]:
    blocks = [CompletionItem(b.name, "keyword", f"{b.name} {{ … }}", b.doc,
                             f"{b.name} {'name ' if b.name in ('material', 'light') else ''}{{\n  \n}}")
              for b in v2_blocks().values()]  # fmt: skip
    return blocks + _statements(analysis)


def _candidates(context: str, analysis: Analysis | None) -> list[CompletionItem]:
    if context.startswith("block:"):
        return _block_keys(context.removeprefix("block:"))
    table: dict[str, Callable[[], list[CompletionItem]]] = {
        "set": _set_keys,
        "raytracer": _raytracer,
        "operator": _ops,
        "rule-modifier": lambda: [CompletionItem(m.name, "modifier", " ".join(m.args), m.doc) for m in modifiers()],
        "rule": lambda: _rules(analysis),
        "color": _colors,
        "preprocessor": lambda: [CompletionItem(w, "preprocessor", "", d, w + " ") for w, d in PREPROCESSOR],
        "function": _functions,
        "v2-statement": lambda: _v2_statements(analysis),
    }
    return table.get(context, lambda: _statements(analysis))()


def _v2_context(text: str, pos: int, line: str) -> str | None:
    """Block keys inside a v2 block, functions inside '( … )', block names at the top level of v2 scripts."""
    block = enclosing_block(text, pos)
    if block is not None:
        return f"block:{block}"
    if line.count("(") > line.count(")"):
        return "function"
    if detect_dialect(text) == 2 and not line.strip() and _brace_depth(text[:pos]) == 0:
        return "v2-statement"
    return None


def _brace_depth(text: str) -> int:
    """Open braces before the cursor, from the lexer (braces in comments do not count)."""
    depth, state = 0, 0
    for line in text.split("\n"):
        tokens, state = lex_line(line, state)
        depth += sum(1 if line[s] == "{" else -1 for s, _, role in tokens if role == "brace")
    return depth


def complete(text: str, pos: int, analysis: Analysis | None = None) -> Completions:
    start_of_line = text.rfind("\n", 0, pos) + 1
    before = text[start_of_line:pos]
    prefix = WORD.search(before).group(0)  # type: ignore[union-attr]
    line = before[: len(before) - len(prefix)]
    if before.lstrip().startswith("#"):
        context, needle = "preprocessor", prefix.lstrip("#").lower()
    elif prefix.lower().startswith("raytracer::") and line.rstrip().lower().endswith("set"):
        context, needle = "raytracer", prefix.lower()
    else:
        context, needle = _v2_context(text, pos, line) or _context(line), prefix.lower()
    items = [i for i in _candidates(context, analysis) if i.label.lower().startswith(needle)]
    start = pos - (len(needle) if context == "preprocessor" else len(prefix))
    return Completions(tuple(items), start, prefix)


PREPROCESSOR = (
    ("define", "#define NAME VALUE — text substitution; add (float:A-B) or (int:A-B) for a slider."),
    ("version", "#version 2 — enable EisenScript v2 extensions (first line)."),
    ("param", "#param NAME TYPE = VALUE range A..B — (v2) a typed parameter with a slider."),
    ("javascript", "#javascript — the script is JavaScript driving the Builder API (Build ▸ Run JavaScript)."),
)


def word_at(text: str, pos: int) -> tuple[int, str]:
    start = pos - len(WORD.search(text[:pos]).group(0))  # type: ignore[union-attr]
    return start, text[start:pos] + HEAD.match(text[pos:]).group(0)  # type: ignore[union-attr]


def hover(text: str, pos: int, analysis: Analysis | None = None) -> str | None:
    start, word = word_at(text, pos)
    return _function_hover(text, start, word) or _word_hover(word.lower().split("::")[0], analysis)


def _function_hover(text: str, start: int, word: str) -> str | None:
    """A v2 expression function, only where it is called (a rule may share the name)."""
    if word not in SIGNATURES or not text[start + len(word) :].lstrip().startswith("("):
        return None
    params, doc = SIGNATURES[word]
    return f"**{word}**({', '.join(params)}) (expression function)\n\n{doc}"


def _word_hover(lower: str, analysis: Analysis | None) -> str | None:
    if not lower:
        return None
    for o in (*operators(), *modifiers()):
        if lower == o.name or lower in {a.name for a in o.aliases}:
            return f"**{o.name}** {' '.join(f'‹{a}›' for a in o.args)}\n\n{o.doc}"
    for p in all_primitives():
        if lower == p.name:
            return f"**{p.name}** (primitive{', v2' if p.v2 else ''})\n\n{p.doc}"
    for s in set_commands():
        if lower == s.key:
            return f"**set {s.key}** ‹{s.value}›\n\n{s.doc}"
    if lower in NAMED_COLORS:
        return "**{}** #{:02x}{:02x}{:02x}".format(lower, *NAMED_COLORS[lower])
    return _rule_hover(analysis, lower)


def _rule_hover(analysis: Analysis | None, name: str) -> str | None:
    if analysis is None:
        return None
    defs = [r for r in analysis.rules if r.name == name]
    if not defs:
        return None
    total = sum(r.weight for r in defs) or 1.0
    lines = [f"**rule {name}** — {_alternatives(analysis, name)}, used {len(analysis.references.get(name, ()))}×"]
    if len(defs) > 1:
        lines += [f"- weight {r.weight:g}: {100 * r.weight / total:.1f}%" for r in defs]
    md = [r.maxdepth for r in defs if r.maxdepth is not None]
    if md:
        lines.append(f"maxdepth {md[0]}")
    return "\n".join(lines)
