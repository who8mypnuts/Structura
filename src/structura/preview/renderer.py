"""The preview engine's frame (docs/08 §5): G-buffer → shadow map → SSAO → lighting composite.

Qt-free: it draws with a ModernGL context handed in by the host (QOpenGLWidget, or a standalone EGL context
in tests and thumbnails). All calls happen on the thread that owns that context.
"""

from __future__ import annotations

import math
from typing import Any

import moderngl
import numpy as np

from ..core.scene.camera import Camera
from .adaptive import AdaptiveQuality
from .camera import Matrices, camera_matrices, gl, look_at, orthographic
from .gpu_scene import GpuScene
from .instances import PreviewScene
from .options import PreviewOptions
from .programs import Programs
from .targets import ShadowTarget, Targets

ACCUMULATE = 16  # jittered frames averaged when the view is still (docs/08 §5 "accumulation AA")


def grid_step(radius: float) -> float:
    """Minor grid spacing: a power of ten so that major lines (×10) are roughly a scene radius apart."""
    return float(10.0 ** math.floor(math.log10(max(radius, 1e-6)))) / 10.0


def halton(i: int, base: int) -> float:
    f, r = 1.0, 0.0
    while i > 0:
        f /= base
        r += f * (i % base)
        i //= base
    return r


def jittered(m: Matrices, sample: int, size: tuple[int, int]) -> Matrices:
    """Sub-pixel projection offset for accumulation sample ``sample`` (0 = centred)."""
    if sample == 0:
        return m
    proj = m.proj.copy()
    proj[0, 2] += (2.0 * halton(sample, 2) - 1.0) / size[0]
    proj[1, 2] += (2.0 * halton(sample, 3) - 1.0) / size[1]
    return Matrices(m.view, proj, m.ortho)


def ssao_kernel(n: int = 16, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.normal(size=(n, 3))
    v[:, 2] = np.abs(v[:, 2]) + 0.05
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    scale = 0.1 + 0.9 * (np.arange(n) / n) ** 2  # more samples close to the point
    return (v * scale[:, None] * rng.uniform(0.5, 1.0, (n, 1))).astype(np.float32)


def _key_dir(m: Matrices, options: PreviewOptions) -> tuple[float, float, float]:
    """The sun direction in view space."""
    v = m.view[:3, :3] @ np.asarray(options.sun_direction, np.float64)
    v /= np.linalg.norm(v) or 1.0
    return (float(v[0]), float(v[1]), float(v[2]))


MASK_WIDTH = 4096  # the highlight mask is a 2-D texture: rows wrap at this width
HIGHLIGHT_UNIT = 12


def _mask_texture(ctx: moderngl.Context, mask: np.ndarray, width: int) -> Any:
    height = -(-len(mask) // width)
    data = np.zeros(width * height, np.uint8)
    data[: len(mask)] = mask
    texture = ctx.texture((width, height), 1, data.tobytes(), dtype="u1")
    texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
    return texture


class PreviewRenderer:
    """The GLSL preview engine: deferred shading with SSAO, shadows, order-independent transparency, picking
    and accumulation anti-aliasing, drawn into any framebuffer of one ModernGL context.
    """

    def __init__(self, ctx: moderngl.Context) -> None:
        """Compiles the programs and creates the render targets' helpers.

        Args:
            ctx: The ModernGL context (current while the renderer is used).
        """
        self.ctx = ctx
        self.programs = Programs(ctx)
        self.gpu: GpuScene | None = None
        self.targets: Targets | None = None
        self.shadow = ShadowTarget(ctx)
        self.kernel = ssao_kernel()
        self._vaos = self.programs.fullscreen
        self.last: Matrices | None = None
        self.samples = 0
        self._key: tuple[object, ...] | None = None
        self._no_highlight = _mask_texture(ctx, np.zeros(1, np.uint8), 1)
        self.highlight: Any = None  # provenance hover: one texel per SceneIR row
        self._highlight_version = 0
        self._scene_version = 0
        self.adaptive = AdaptiveQuality(ctx)
        self.reduced = False  # the last frame skipped SSAO (the camera moves and full frames are slow)
        self._shadow_key: tuple[object, ...] | None = None
        self._light: np.ndarray | None = None

    # -- scene -----------------------------------------------------------------------------------------
    def set_scene(self, scene: PreviewScene | None) -> None:
        """Uploads a scene (replacing and releasing the previous one); the next frame starts accumulating again.

        Args:
            scene: The preview scene, or None for an empty view.
        """
        if self.gpu is not None:
            self.gpu.release()
        self._shadow_key = None
        self._scene_version += 1  # (not id(): a freed GpuScene's id is often reused by the next one)
        self.gpu = GpuScene(self.ctx, self.programs, scene) if scene is not None else None

    def set_highlight(self, rows: np.ndarray | None, count: int) -> None:
        """Tint the instances of ``rows`` (SceneIR rows, e.g. everything one call site produced)."""
        if self.highlight is not None:
            self.highlight.release()
        self.highlight = None
        if rows is not None and len(rows) and count:
            mask = np.zeros(count, np.uint8)
            mask[rows[rows < count]] = 1
            self.highlight = _mask_texture(self.ctx, mask, min(count, MASK_WIDTH))
        self._highlight_version += 1

    @property
    def scene(self) -> PreviewScene | None:
        return self.gpu.scene if self.gpu is not None else None

    # -- frame -----------------------------------------------------------------------------------------
    def render(
        self, camera: Camera, target: Any, size: tuple[int, int], options: PreviewOptions, accumulate: bool = True
    ) -> int:
        """Draws one frame into a target.

        Args:
            camera: The camera to view through.
            target: The framebuffer to draw into.
            size: (width, height) in pixels.
            options: Look, effects, background, selection and the grid.
            accumulate: Whether frames of an unchanged view accumulate anti-aliasing samples.

        Returns:
            The number of accumulated samples now shown (ACCUMULATE once converged).
        """
        w, h = max(1, size[0]), max(1, size[1])
        if self.targets is None or self.targets.size != (w, h):
            if self.targets is not None:
                self.targets.release()
            self.targets = Targets(self.ctx, w, h)
        key = (camera, (w, h), options, self._scene_version, self._highlight_version)
        moving = accumulate and key != self._key
        if not accumulate or key != self._key or self.samples >= ACCUMULATE:
            self.samples = 0 if (not accumulate or key != self._key) else self.samples
        self._key = key
        if self.samples >= ACCUMULATE:
            self._present(target, (w, h))  # converged: redisplay without new work
            return self.samples
        self.reduced = self.adaptive.reduced(moving)
        with self.adaptive.measure(self.reduced):
            self._frame(camera, (w, h), options)
        self._present(target, (w, h))
        return self.samples

    def _frame(self, camera: Camera, size: tuple[int, int], options: PreviewOptions) -> None:
        assert self.targets is not None
        scene = self.scene
        lo, hi = (scene.lo, scene.hi) if scene is not None else (np.full(3, -1.0), np.full(3, 1.0))
        self.last = camera_matrices(camera, size[0] / size[1], lo, hi)
        m = jittered(self.last, self.samples, size)
        self._geometry(m, size, options)
        light = self._shadows(lo, hi, options) if options.effects & 2 else np.eye(4)
        effects = options.effects & ~1 if self.reduced else options.effects
        if effects & 1 and scene is not None:
            self._ssao(m, scene.feature_size)
        oit = self._transparent(m, size, options)
        self._composite(m, light, self.targets.frame_fbo, size, options, oit, effects)
        self._accumulate()

    @property
    def converged(self) -> bool:
        return self.samples >= ACCUMULATE

    def _accumulate(self) -> None:
        assert self.targets is not None
        t = self.targets
        t.accum_fbo.use()
        if self.samples == 0:
            t.accum_fbo.clear(0.0, 0.0, 0.0, 0.0)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.ONE, moderngl.ONE
        t.frame.use(0)
        self.programs.copy["u_source"].value = 0
        self._vaos["copy"].render(moderngl.TRIANGLES, vertices=3)
        self.ctx.disable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.samples += 1

    def _present(self, target: Any, size: tuple[int, int]) -> None:
        assert self.targets is not None
        target.use()
        target.viewport = (0, 0, *size)
        self.targets.accum.use(0)
        self.programs.present["u_accum"].value = 0
        self.programs.present["u_inv_count"].value = 1.0 / max(1, self.samples)
        self._vaos["present"].render(moderngl.TRIANGLES, vertices=3)

    def _frame_uniforms(self, m: Matrices, viewport: tuple[int, int], options: PreviewOptions) -> Any:
        key_dir = _key_dir(m, options)

        def apply(program: Any) -> None:
            program["u_view"].write(gl(m.view))
            program["u_proj"].write(gl(m.proj))
            if "u_viewport" in program:
                program["u_viewport"].value = (float(viewport[0]), float(viewport[1]))
            if "u_ortho" in program:
                program["u_ortho"].value = int(m.ortho)
            if "u_width" in program:
                program["u_width"].value = options.line_width
            if "u_key_dir" in program:
                program["u_key_dir"].value = key_dir

        return apply

    def _draw_scene(
        self, m: Matrices, viewport: tuple[int, int], options: PreviewOptions, pass_: str = "gbuffer"
    ) -> None:
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.CULL_FACE)
        if pass_ == "gbuffer":
            self.ctx.disable(moderngl.BLEND)
        if self.gpu is not None:
            self.gpu.render(pass_, self._frame_uniforms(m, viewport, options))

    def _transparent(self, m: Matrices, size: tuple[int, int], options: PreviewOptions) -> bool:
        """Weighted blended OIT over the opaque depth; returns False when nothing is see-through."""
        if self.gpu is None or not self.gpu.has_pass("accum"):
            return False
        assert self.targets is not None
        t, ctx = self.targets, self.ctx
        ctx.enable(moderngl.BLEND)
        for fbo, clear, blend, pass_ in (
            (t.oit_accum_fbo, 0.0, (moderngl.ONE, moderngl.ONE), "accum"),
            (t.oit_reveal_fbo, 1.0, (moderngl.ZERO, moderngl.ONE_MINUS_SRC_COLOR), "reveal"),
        ):
            fbo.depth_mask = False  # test against the opaque depth, never write it
            fbo.use()
            fbo.viewport = (0, 0, *size)
            fbo.clear(clear, clear, clear, clear)
            ctx.blend_func = blend
            self._draw_scene(m, size, options, pass_)
        ctx.disable(moderngl.BLEND)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        t.gbuffer.color_mask = [(False,) * 4, (False,) * 4, (False,) * 4, (True,) * 4]  # type: ignore[assignment]
        t.gbuffer.depth_mask = False
        t.gbuffer.use()  # see-through surfaces in front of the opaque ones become pickable
        self._draw_scene(m, size, options, "pick")
        t.gbuffer.color_mask = [(True,) * 4] * 4  # type: ignore[assignment]
        t.gbuffer.depth_mask = True
        return True

    def _geometry(self, m: Matrices, size: tuple[int, int], options: PreviewOptions) -> None:
        assert self.targets is not None
        fbo = self.targets.gbuffer
        fbo.use()
        fbo.viewport = (0, 0, *size)
        fbo.clear(0.0, 0.0, 0.0, 0.0, depth=1.0)
        self._draw_scene(m, size, options)

    def _shadows(self, lo: np.ndarray, hi: np.ndarray, options: PreviewOptions) -> np.ndarray:
        """The sun's shadow map; it depends on the scene and the sun only, so camera moves reuse it."""
        key = (id(self.gpu), tuple(np.round(lo, 6)), tuple(np.round(hi, 6)), options.sun_direction, options.line_width)
        if key == self._shadow_key and self._light is not None:
            return self._light
        self._shadow_key, self._light = key, self._render_shadows(lo, hi, options)
        return self._light

    def _render_shadows(self, lo: np.ndarray, hi: np.ndarray, options: PreviewOptions) -> np.ndarray:
        centre, radius = (lo + hi) / 2.0, max(float(np.linalg.norm(hi - lo)) / 2.0, 1e-3)
        sun = np.asarray(options.sun_direction, np.float64)
        up = np.array([0.0, 0.0, 1.0]) if abs(sun[1]) > 0.99 else np.array([0.0, 1.0, 0.0])
        view = look_at(centre + sun * radius * 2.0, centre, up)
        light = Matrices(view, orthographic(radius, 1.0, radius * 0.5, radius * 3.5), ortho=True)
        fbo = self.shadow.fbo
        fbo.use()
        fbo.viewport = (0, 0, *self.shadow.depth.size)
        fbo.clear(depth=1.0)
        self._draw_scene(light, self.shadow.depth.size, options)
        result: np.ndarray = light.proj @ light.view
        return result

    def _ssao(self, m: Matrices, feature: float) -> None:
        assert self.targets is not None
        t, p = self.targets, self.programs
        self.ctx.disable(moderngl.DEPTH_TEST)
        t.ao_fbo[0].use()
        t.depth.use(0)
        t.normal.use(1)
        p.ssao["u_depth"].value, p.ssao["u_normal"].value = 0, 1
        p.ssao["u_inv_proj"].write(gl(m.inv_proj))
        p.ssao["u_proj"].write(gl(m.proj))
        p.ssao["u_radius"].value = feature * 1.5
        p.ssao["u_kernel"].write(self.kernel.tobytes())
        self._vaos["ssao"].render(moderngl.TRIANGLES, vertices=3)
        t.ao_fbo[1].use()
        t.ao[0].use(0)
        p.blur["u_source"].value = 0
        self._vaos["blur"].render(moderngl.TRIANGLES, vertices=3)

    def _composite(
        self, m: Matrices, light: np.ndarray, target: Any, size: tuple[int, int], options: PreviewOptions, oit: bool,
        effects: int,
    ) -> None:  # fmt: skip
        assert self.targets is not None
        t, prog = self.targets, self.programs.composite
        target.use()
        target.viewport = (0, 0, *size)
        self.ctx.disable(moderngl.DEPTH_TEST | moderngl.BLEND)
        for unit, (name, tex) in enumerate(
            (("u_albedo", t.albedo), ("u_normal", t.normal), ("u_id", t.ids), ("u_pick", t.pick), ("u_depth", t.depth),
             ("u_ao", t.ao[1]), ("u_shadow", self.shadow.depth), ("u_oit_accum", t.oit_accum),
             ("u_oit_reveal", t.oit_reveal))
        ):  # fmt: skip
            tex.use(unit)
            prog[name].value = unit
        (self.highlight or self._no_highlight).use(HIGHLIGHT_UNIT)
        prog["u_highlight"].value, prog["u_highlight_on"].value = HIGHLIGHT_UNIT, int(self.highlight is not None)
        inv_view = m.inv_view
        values = {
            "u_inv_proj": gl(m.inv_proj),
            "u_view_to_light": gl(light @ inv_view),
            "u_view_to_world": gl(inv_view),
        }
        for name, data in values.items():
            prog[name].write(data)
        prog["u_key_dir"].value = _key_dir(m, options)
        prog["u_oit"].value = int(oit)
        prog["u_key_color"].value, prog["u_sky"].value, prog["u_ground"].value = (
            options.key,
            options.sky,
            options.ground,
        )
        prog["u_bg_top"].value, prog["u_bg_bottom"].value = options.background_top, options.background_bottom
        prog["u_look"].value, prog["u_effects"].value = options.look_index, effects
        prog["u_exposure"].value = options.exposure
        prog["u_selected"].value = 0 if options.selected is None else options.selected + 1
        prog["u_select_color"].value = tuple(float(v) ** 2.2 for v in options.select_color)
        self._grid_uniforms(prog, options)
        self._vaos["composite"].render(moderngl.TRIANGLES, vertices=3)

    def _grid_uniforms(self, prog: Any, options: PreviewOptions) -> None:
        """The ground grid lies under the structure, with a step that keeps about ten major cells across it."""
        scene = self.scene
        prog["u_grid"].value = int(options.grid and scene is not None)
        if scene is None:
            return
        lo, hi = np.asarray(scene.lo, np.float64), np.asarray(scene.hi, np.float64)
        radius = max(float(np.linalg.norm(hi - lo)) / 2.0, 1e-3)
        prog["u_grid_plane"].value = (float(lo[1]), float((lo[0] + hi[0]) / 2), float((lo[2] + hi[2]) / 2), radius * 6)
        prog["u_grid_step"].value = grid_step(radius)
        prog["u_grid_color"].value = options.grid_color

    # -- picking ---------------------------------------------------------------------------------------
    def pick(self, x: int, y: int) -> int | None:
        """SceneIR row under pixel (x, y) of the last frame (y from the top), or None for the background."""
        if self.targets is None:
            return None
        w, h = self.targets.size
        if not (0 <= x < w and 0 <= y < h):
            return None
        data = self.targets.gbuffer.read(viewport=(x, h - 1 - y, 1, 1), attachment=3, components=1, dtype="u4")
        value = int(np.frombuffer(data, np.uint32)[0])
        return value - 1 if value else None

    def release(self) -> None:
        self.set_scene(None)
        self.set_highlight(None, 0)
        self._no_highlight.release()
        if self.targets is not None:
            self.targets.release()
        self.shadow.release()
        self.adaptive.release()
