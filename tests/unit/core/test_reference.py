"""The generated language reference (docs/12 §2.2): complete, anchored, up to date in docs/."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from structura.core.lang.assist import complete
from structura.core.lang.catalog import diagnostic_specs, operators, primitives, set_commands, v2_blocks
from structura.core.lang.reference import anchor_at, anchors, to_html

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ("#version 2\nset maxdepth 20\nmaterial gold {\n  roughness 0.2\n}\n"
          "rule r md 9 { { rx (sin(30)) s 0.9 } r box::gold }\nset raytracer::samples 4\n")  # fmt: skip


def test_every_catalogue_entry_has_an_anchor() -> None:
    known = anchors()
    assert {f"op-{o.name}" for o in operators()} <= known
    assert {f"prim-{p.name}" for p in primitives()} <= known
    assert {f"set-{s.key}" for s in set_commands()} <= known
    assert {f"diag-{c}" for c in diagnostic_specs()} <= known
    assert {f"block-material-{k.name}" for k in v2_blocks()["material"].keys} <= known
    html = to_html()
    assert all(f'<a name="{a}">' in html for a in known)


@pytest.mark.parametrize(
    ("word", "offset", "anchor"),
    [("maxdepth", 1, "set-maxdepth"), ("roughness", 1, "block-material-roughness"), ("rx", 1, "op-rx"),
     ("sin", 1, "fn-sin"), ("box::gold", 1, "prim-box"), ("md", 1, "op-maxdepth"), ("samples", 1, "rt-samples"),
     ("version", 1, "kw-version"), ("material", 1, "block-material")],
)  # fmt: skip
def test_anchor_at_the_word_under_the_cursor(word: str, offset: int, anchor: str) -> None:
    assert anchor_at(SCRIPT, SCRIPT.index(word) + offset) == anchor


def test_generated_docs_are_up_to_date() -> None:
    result = subprocess.run([sys.executable, "tools/gen_reference.py", "--check"], cwd=ROOT, capture_output=True,
                            text=True, check=False)  # fmt: skip
    assert result.returncode == 0, result.stdout


def test_v2_completion_contexts() -> None:
    def labels(text: str) -> list[str]:
        return [i.label for i in complete(text, len(text)).items]

    assert labels("#version 2\nmaterial gold {\n  rou") == ["roughness"]
    assert labels("#version 2\nbox\n")[:5] == ["material", "light", "environment", "camera", "render"]
    assert labels("{ x (si") == ["sin"]
    assert "include" not in labels("#") and "param" in labels("#")
