"""Preview engine, rendered headless through EGL (Mesa llvmpipe in CI; docs/08)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import numpy as np
import pytest

from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.camera import Camera, framed
from structura.preview.instances import preview_scene
from structura.preview.options import PreviewOptions
from structura.preview.renderer import ACCUMULATE, PreviewRenderer

moderngl = pytest.importorskip("moderngl")
W, H = 96, 72
SCRIPT = """
{ x -1.6 color #f00 } box
{ x 0 color #0f0 } sphere
{ x 1.6 color #00f alpha 0.5 } box
{ y 1.4 s 3 0.1 0.1 } line
{ y -1.4 } grid
{ y -1.4 x 1.5 } triangle[0,0,0;1,0,0;0,1,0]
"""


@pytest.fixture(scope="module")
def ctx() -> Iterator[Any]:
    try:
        context = moderngl.create_standalone_context(require=330, backend="egl")
    except Exception as exc:
        pytest.skip(f"no OpenGL 3.3: {exc}")
    yield context
    context.release()


@pytest.fixture(scope="module")
def setup(ctx: Any) -> tuple[PreviewRenderer, Any, Camera]:
    scene = build_scene(compile_script(SCRIPT).program).scene
    renderer = PreviewRenderer(ctx)
    ps = preview_scene(scene)
    renderer.set_scene(ps)
    camera = framed(Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0)), ps.lo, ps.hi, W / H)
    fbo = ctx.framebuffer([ctx.texture((W, H), 4)])
    return renderer, fbo, camera


def _image(fbo: Any) -> np.ndarray:
    return np.frombuffer(fbo.read(components=4), np.uint8).reshape(H, W, 4)[::-1, :, :3]


def test_every_pipeline_draws_something(setup: tuple[PreviewRenderer, Any, Camera]) -> None:
    renderer, fbo, camera = setup
    renderer.render(camera, fbo, (W, H), PreviewOptions(), accumulate=False)
    image = _image(fbo).astype(int)
    left, middle = image[H // 2, W // 4], image[H // 2, W // 2]
    assert left[0] > left[1] + 40 and left[0] > left[2] + 40  # the red box
    assert middle[1] > middle[0] + 30 and middle[1] > middle[2] + 30  # the green sphere
    ids = {renderer.pick(x, y) for x in range(W) for y in range(H)}
    assert {0, 1, 2, 3, 4, 5} <= ids  # box, sphere, see-through box, line, grid, triangle are all pickable


def test_picking_maps_pixels_to_scene_rows(setup: tuple[PreviewRenderer, Any, Camera]) -> None:
    renderer, fbo, camera = setup
    renderer.render(camera, fbo, (W, H), PreviewOptions(), accumulate=False)
    assert renderer.pick(W // 4, H // 2) == 0
    assert renderer.pick(W // 2, H // 2) == 1
    assert renderer.pick(0, 0) is None


def test_transparency_shows_the_background_through(setup: tuple[PreviewRenderer, Any, Camera]) -> None:
    renderer, fbo, camera = setup
    options = PreviewOptions(background_top=(1.0, 1.0, 0.0), background_bottom=(1.0, 1.0, 0.0), ssao=False)
    renderer.render(camera, fbo, (W, H), options, accumulate=False)
    r, _, b = _image(fbo)[H // 2, 3 * W // 4].astype(int)
    assert b > 60 and r > 60  # blue box blended with the yellow backdrop


def test_accumulation_converges_and_then_stops(setup: tuple[PreviewRenderer, Any, Camera]) -> None:
    renderer, fbo, camera = setup
    options = PreviewOptions(look="legacy")
    counts = [renderer.render(camera, fbo, (W, H), options) for _ in range(ACCUMULATE + 3)]
    assert counts[:3] == [1, 2, 3] and counts[-1] == ACCUMULATE and renderer.converged
    moved = Camera(camera.eye, (0.1, 0.0, 0.0))
    assert renderer.render(moved, fbo, (W, H), options) == 1  # any change restarts


def test_empty_scene_draws_the_background(ctx: Any) -> None:
    renderer = PreviewRenderer(ctx)
    fbo = ctx.framebuffer([ctx.texture((W, H), 4)])
    bg = (0.2, 0.4, 0.6)
    renderer.render(Camera((0, 0, 5), (0, 0, 0)), fbo, (W, H), PreviewOptions(background_top=bg, background_bottom=bg))
    pixel = _image(fbo)[H // 2, W // 2]
    assert np.abs(pixel.astype(int) - [124, 170, 203]).max() <= 2  # sRGB of the linear backdrop
    renderer.release()


def test_highlight_tints_only_the_highlighted_rows(setup: tuple[PreviewRenderer, Any, Camera]) -> None:
    renderer, fbo, camera = setup
    options = PreviewOptions(ssao=False, shadows=False)
    renderer.render(camera, fbo, (W, H), options, accumulate=False)
    before = _image(fbo).astype(int)
    renderer.set_highlight(np.array([1]), 6)  # the green sphere
    renderer.render(camera, fbo, (W, H), options, accumulate=False)
    after = _image(fbo).astype(int)
    renderer.set_highlight(None, 0)
    sphere, box = (H // 2, W // 2), (H // 2, W // 4)
    assert after[sphere][0] > before[sphere][0] + 30  # pulled towards the orange highlight colour
    assert np.abs(after[box] - before[box]).max() <= 2  # other rows untouched


def test_ground_grid_shows_below_the_structure_only(setup: tuple[PreviewRenderer, Any, Camera]) -> None:
    renderer, fbo, camera = setup
    above = Camera((camera.eye[0], camera.eye[1] + 6.0, camera.eye[2]), camera.target)  # looking down on the grid
    bg = (0.0, 0.0, 0.0)
    plain = PreviewOptions(background_top=bg, background_bottom=bg, ssao=False, shadows=False)
    renderer.render(above, fbo, (W, H), plain, accumulate=False)
    without = _image(fbo).astype(int)
    renderer.render(above, fbo, (W, H), PreviewOptions(**{**plain.__dict__, "grid": True}), accumulate=False)
    with_grid = _image(fbo).astype(int)
    changed = np.abs(with_grid - without).max(axis=2) > 8
    background = np.array([[renderer.pick(x, y) is None for x in range(W)] for y in range(H)])
    assert changed[background].mean() > 0.02  # lines on the empty ground
    assert changed[H // 2, W // 2] == 0 or not background[H // 2, W // 2]  # the sphere hides the grid


def test_technical_look_draws_edges(setup: tuple[PreviewRenderer, Any, Camera]) -> None:
    renderer, fbo, camera = setup
    renderer.render(camera, fbo, (W, H), PreviewOptions(look="flat"), accumulate=False)
    flat = _image(fbo).astype(int)
    renderer.render(camera, fbo, (W, H), PreviewOptions(look="technical"), accumulate=False)
    technical = _image(fbo).astype(int)
    darker = flat.max(axis=2) - technical.max(axis=2) > 80
    assert darker.sum() > 10  # outlines where the flat look has colour
