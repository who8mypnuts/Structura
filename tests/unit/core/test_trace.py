"""Show Ancestry: the traced build agrees with the real one (docs/06 §10.4)."""

from __future__ import annotations

import pytest

from structura.core.build.api import build_scene
from structura.core.build.trace import ancestry
from structura.core.lang.api import compile_script

SCRIPTS = [
    "R\nrule R md 4 { { x 1 } R box }\n",
    "set recursion depth\nR\nrule R md 4 { { x 1 } R { y 1 } R box }\n",  # depth-first
    "set maxdepth 6\nR\nrule R w 1 { { x 1 rz 30 } R sphere }\nrule R w 1 { { y 1 } R R box }\n",  # ambiguous
]


@pytest.mark.parametrize("text", SCRIPTS)
def test_every_chain_starts_at_the_top_and_follows_the_call_sites(text: str) -> None:
    program = compile_script(text).program
    scene = build_scene(program, 3).scene
    for row in range(0, len(scene), max(1, len(scene) // 25)):  # a sample of rows
        steps = ancestry(program, 3, row)
        assert steps[0].rule == program.top and steps[0].action == -1
        assert all(program.act_target[s.action] == s.rule for s in steps[1:])
        assert len(steps) == scene.generation[row] + 1  # one application per generation


def test_rows_that_were_not_built_are_reported() -> None:
    program = compile_script("box\n").program
    with pytest.raises(ValueError, match="not emitted"):
        ancestry(program, 0, 5)
