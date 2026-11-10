"""Lighting rigs (PLAN F3): every rig writes clean v2 text, sized to the structure, replacing an earlier rig."""

from __future__ import annotations

import numpy as np
import pytest

from structura.core.build.api import build_scene
from structura.core.lang.analysis import analyze
from structura.core.lang.api import compile_script
from structura.core.scene.light_rigs import MARKER_LINE, PREFIX, apply_rig, light_entries, rigs

LO, HI = np.array([-1.0, -1.0, -1.0]), np.array([1.0, 1.0, 1.0])
SCRIPT = "#version 2\nlight mine { type point position [0 5 0] power 10 }\n{ s 2 } sphere\n"


@pytest.mark.parametrize("name", list(rigs()))
def test_each_rig_is_clean_v2(name: str) -> None:
    rig = rigs()[name]
    text = apply_rig(SCRIPT, rig, LO, HI)
    assert [d.code for d in analyze(text).diagnostics if d.severity.name != "INFO"] == []
    decl = build_scene(compile_script(text).program).scene.declarations
    assert decl is not None and decl.environment["type"] == rig.environment["type"]
    names = [light.name for light in decl.lights]
    assert names == ["mine", *(PREFIX + spec["name"] for spec in rig.lights)]  # the user's light stays


def test_applying_another_rig_replaces_the_first() -> None:
    text = SCRIPT
    for rig in rigs().values():
        text = apply_rig(text, rig, LO, HI)
    last = list(rigs().values())[-1]
    assert len(MARKER_LINE.findall(text)) == 1 and text.count("environment") == 1
    assert text.count(f"light {PREFIX}") == len(last.lights)


def test_rigs_scale_with_the_structure() -> None:
    spec = rigs()["Studio softbox"].lights[0]
    small, large = light_entries(spec, LO, HI), light_entries(spec, LO * 10, HI * 10)
    np.testing.assert_allclose(large["position"], np.multiply(small["position"], 10))
    assert large["power"] == pytest.approx(small["power"] * 100)  # the same light at the structure
    assert large["size"] == pytest.approx(tuple(v * 10 for v in small["size"]))


def test_rig_looks_exist() -> None:
    from structura.render.post import LOOKS  # noqa: PLC0415

    assert all(rig.look in LOOKS for rig in rigs().values() if rig.look)
    assert len(rigs()) == 7
