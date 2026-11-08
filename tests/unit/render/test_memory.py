"""The memory guard's estimate and verdict (docs/09 §8)."""

from __future__ import annotations

from dataclasses import replace

from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.ir import SceneIR
from structura.render.memory import MIB, guard_message, render_bytes
from structura.render.settings import RenderSettings


def _scene(text: str) -> SceneIR:
    program = compile_script(text).program
    assert program is not None
    return build_scene(program, 1).scene


def test_the_estimate_grows_with_the_scene_the_image_and_the_aovs() -> None:
    small, big = _scene("sphere"), _scene("100 * { x 1 } box")
    settings = RenderSettings(width=64, height=64)
    assert render_bytes(big, settings) > render_bytes(small, settings)
    assert render_bytes(small, replace(settings, width=128)) > render_bytes(small, settings)
    assert render_bytes(small, replace(settings, aovs=True)) > render_bytes(small, settings)


def test_the_guard_refuses_only_what_exceeds_its_share_of_free_memory() -> None:
    assert guard_message(50 * MIB, 100 * MIB, 80) is None
    message = guard_message(90 * MIB, 100 * MIB, 80)
    assert message is not None and "90 MB" in message and "80 %" in message
