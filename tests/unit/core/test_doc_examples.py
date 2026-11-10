"""The EisenScript v2 examples in the documentation are clean: every fenced block that starts with
'#version 2' in the user guide, the language docs and the README compiles without errors, and so do the block
snippets of the language spec's §9 (material, light, environment, camera, render) inside a v2 script."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from structura.core.lang.analysis import analyze

ROOT = Path(__file__).resolve().parents[3]
DOCS = [ROOT / "README.md", ROOT / "docs/05-eisenscript-language.md", *sorted((ROOT / "docs/user-guide").glob("*.md"))]
FENCE = re.compile(r"```[a-z]*\n(#version 2\n.*?)```", re.S)
SNIPPET = re.compile(r"```\n((?:material|light|camera|render|environment)\b.*?)```", re.S)


def _examples() -> list[tuple[str, str]]:
    found = [(f"{path.name}#{i}", block) for path in DOCS for i, block in enumerate(FENCE.findall(path.read_text()))]
    spec = (ROOT / "docs/05-eisenscript-language.md").read_text()
    return found + [(f"05§9 snippet {i}", f"#version 2\n{block}box\n") for i, block in enumerate(SNIPPET.findall(spec))]


@pytest.mark.parametrize(("where", "text"), _examples(), ids=[w for w, _ in _examples()])
def test_documented_v2_example_has_no_errors(where: str, text: str) -> None:
    errors = [(d.code, d.message) for d in analyze(text).diagnostics if d.severity.name == "ERROR"]
    assert errors == [], where
