"""The language reference (docs/12 §2.2 'F1', docs/reference/language.md), generated from the catalogues so
it can never disagree with the editor's completion and hover. Qt-free: one data model, rendered as
Markdown (docs) or HTML (the in-app browser). ``anchor_at`` maps the word under the cursor to its entry."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from functools import cache

from .catalog import (
    all_primitives,
    diagnostic_specs,
    modifiers,
    operator_names,
    operators,
    raytracer_keys,
    set_commands,
    v2_blocks,
)
from .signatures import CONSTANTS, SIGNATURES
from .v2.blocks import enclosing_block

STATEMENTS = (
    ("rule", "rule NAME [maxdepth N [> OTHER]] [weight W] { … }",
     "Define a rule. Several definitions with the same name form an ambiguous rule: one is chosen at random, "
     "in proportion to the weights. maxdepth limits the recursion depth; '> OTHER' calls OTHER when the limit "
     "is reached."),
    ("set", "set KEY VALUE", "Change a build, view or render setting (see Settings)."),
    ("loop", "N * { operators } RULE", "Apply the transformation N times, calling RULE after each step. "
     "'{ operators } RULE' is a single step; several loops can be chained."),
    ("define", "#define NAME VALUE [(float:A-B) | (int:A-B)]",
     "Text substitution (v1: inside words too, W103). A range turns the define into a Parameters slider."),
    ("version", "#version 2", "First line: enable EisenScript v2 (blocks, #param, expressions, whole-word defines)."),
    ("param", "#param NAME TYPE = VALUE [range A..B] [\"Label\"]", "(v2) A typed parameter with a slider."),
    ("comment", "// line, /* block */", "Comments."),
)  # fmt: skip
_WORD = re.compile(r"[A-Za-z_][\w:.\-]*")


@dataclass(frozen=True)
class Entry:
    anchor: str
    name: str
    signature: str
    doc: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Section:
    anchor: str
    title: str
    intro: str
    entries: tuple[Entry, ...]


def _operator_entries() -> tuple[Entry, ...]:
    return tuple(Entry(f"op-{o.name}", o.name, " ".join([o.name, *(f"‹{a}›" for a in o.args)]), o.doc,
                       tuple(a.name for a in o.aliases)) for o in operators())  # fmt: skip


def _block_entries() -> tuple[Entry, ...]:
    entries = []
    for block in v2_blocks().values():
        entries.append(Entry(f"block-{block.name}", block.name, f"{block.name} {{ key value … }}", block.doc))
        entries += [Entry(f"block-{block.name}-{k.name}", f"{block.name} · {k.name}", f"{k.name} ‹{k.value}›", k.doc)
                    for k in block.keys]  # fmt: skip
    return tuple(entries)


@cache
def sections() -> tuple[Section, ...]:
    fns = tuple(Entry(f"fn-{name}", name, f"{name}({', '.join(params)})", doc)
                for name, (params, doc) in SIGNATURES.items())  # fmt: skip
    consts = tuple(Entry(f"fn-{name}", name, name, doc) for name, doc in CONSTANTS.items())
    return (
        Section("statements", "Statements", "The structure of a script.",
                tuple(Entry(f"kw-{k}", k, sig, doc) for k, sig, doc in STATEMENTS)),
        Section("operators", "Transformations", "Inside '{ … }'. Transformations apply in the current (local) frame.",
                _operator_entries()),
        Section("modifiers", "Rule modifiers", "After 'rule NAME'.",
                tuple(Entry(f"op-{m.name}", m.name, " ".join([m.name, *(f"‹{a}›" for a in m.args)]), m.doc,
                            tuple(a.name for a in m.aliases)) for m in modifiers())),
        Section("primitives", "Primitives", "Built-in shapes; 'box::tag' selects a material or render class.",
                tuple(Entry(f"prim-{p.name}", p.name, f"{p.name}[r]" if p.param is not None else p.name, p.doc)
                      for p in all_primitives())),
        Section("settings", "Settings", "'set KEY VALUE' at the top level or inside a rule.",
                tuple(Entry(f"set-{s.key}", s.key, f"set {s.key} ‹{s.value}›", s.doc, s.aliases)
                      for s in set_commands())),
        Section("raytracer", "Raytracer settings", "'set raytracer::KEY value' (Structure Synth 1.5 renderer).",
                tuple(Entry(f"rt-{k.name}", k.name, f"set raytracer::{k.name} ‹{k.value}›", k.doc)
                      for k in raytracer_keys())),
        Section("blocks", "v2 blocks", "Top-level blocks of EisenScript v2 ('#version 2').", _block_entries()),
        Section("expressions", "v2 expressions", "'( expression )' wherever a number is expected. Angles are in "
                "degrees.", fns + consts),
        Section("diagnostics", "Diagnostics", "Problems reported while you type.",
                tuple(Entry(f"diag-{d.code}", d.code, f"{d.code} · {d.severity}", f"{d.title}. {d.doc}")
                      for d in diagnostic_specs().values())),
    )  # fmt: skip


def anchors() -> set[str]:
    return {e.anchor for s in sections() for e in s.entries}


# -- rendering -----------------------------------------------------------------------------------------------
def to_markdown() -> str:
    out = ["# EisenScript language reference", "",
           "Generated from the language catalogues (`tools/gen_reference.py`); do not edit by hand.", ""]  # fmt: skip
    for section in sections():
        out += [f"## {section.title}", "", section.intro, "", "| Name | Form | Description |", "|---|---|---|"]
        for e in section.entries:
            aliases = f" (also: {', '.join(e.aliases)})" if e.aliases else ""
            cells = (f"`{e.name}`", f"`{e.signature}`", e.doc + aliases)
            out.append("| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
        out.append("")
    return "\n".join(out)


def to_html() -> str:
    out = ["<h1>EisenScript language reference</h1>"]
    out.append("<p>" + " · ".join(f'<a href="#{s.anchor}">{html.escape(s.title)}</a>' for s in sections()) + "</p>")
    for section in sections():
        out.append(f'<h2><a name="{section.anchor}"></a>{html.escape(section.title)}</h2>')
        out.append(f"<p>{html.escape(section.intro)}</p>")
        for e in section.entries:
            aliases = f" <i>(also: {html.escape(', '.join(e.aliases))})</i>" if e.aliases else ""
            out.append(f'<p><a name="{e.anchor}"></a><b><code>{html.escape(e.signature)}</code></b>{aliases}<br/>'
                       f"{html.escape(e.doc)}</p>")  # fmt: skip
    return "\n".join(out)


# -- the entry for the word under the cursor -------------------------------------------------------------------
def _word_at(text: str, pos: int) -> tuple[int, str]:
    for match in _WORD.finditer(text, max(0, text.rfind("\n", 0, pos) + 1)):
        if match.start() <= pos <= match.end():
            return match.start(), match.group(0)
        if match.start() > pos:
            break
    return pos, ""


def _line_before(text: str, start: int) -> str:
    return text[text.rfind("\n", 0, start) + 1 : start]


def anchor_at(text: str, pos: int) -> str | None:
    """The reference anchor for the symbol at ``pos`` ('op-rx', 'set-maxdepth', 'block-material-ior' …)."""
    start, word = _word_at(text, pos)
    lower = word.lower()
    before = _line_before(text, start).rstrip()
    if before.lstrip().startswith("#") or lower.startswith("#"):
        directive = (before + word).lstrip("# ").split()[0] if (before + word).strip("# ") else ""
        return f"kw-{directive}" if f"kw-{directive}" in anchors() else None
    block = enclosing_block(text, pos)
    candidates = [
        f"block-{block}-{lower.replace('-', '_')}" if block else "",
        f"rt-{lower.removeprefix('raytracer::')}" if lower.startswith("raytracer::") else "",
        f"set-{lower}" if before.endswith("set") else "",
        f"fn-{lower}" if text[start + len(word) :].lstrip().startswith("(") or lower in CONSTANTS else "",
        f"block-{lower}" if lower in v2_blocks() and not before else "",
        f"op-{operator_names().get(lower, (lower, True))[0]}",
        f"prim-{lower.split('::')[0]}",
        f"kw-{lower}",
    ]
    known = anchors()
    return next((c for c in candidates if c in known), None)
