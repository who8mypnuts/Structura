"""Upload a PreviewScene to ModernGL buffers and build the vertex arrays of every pipeline (docs/08 §3–4).

Opaque instances are drawn into the G-buffer; see-through ones (alpha < 1) in the two OIT passes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import moderngl
import numpy as np

from ..core.geometry.unit_shapes import unit_box
from .instances import Batch, PreviewScene, TriangleSoup
from .programs import Programs

INSTANCE_LAYOUT = [("4f 4f 4f/i", "i_r0", "i_r1", "i_r2"), ("4f1/i", "i_color"), ("u/i", "i_id")]
QUAD = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]], np.float32)
QUAD_INDICES = np.array([0, 1, 2, 0, 2, 3], np.uint32)
OPAQUE_PASSES, SEE_THROUGH_PASSES = ("gbuffer",), ("accum", "reveal", "pick")
PROGRAM_OF = {"gbuffer": "gbuffer", "pick": "gbuffer", "accum": "accum", "reveal": "reveal"}
DOT_RADIUS = 0.05  # world units, as in the precision engine's packing


@dataclass
class Draw:
    vaos: dict[str, Any]  # render pass → vertex array
    instances: int
    vertices: int = 0  # > 0: non-indexed draw with this many vertices per instance
    uniforms: dict[str, Any] = field(default_factory=dict)
    front: str | None = None  # cull back faces with this front-face winding; None: no culling


class _Buffers:
    """Creates GL buffers and remembers them for release."""

    def __init__(self, ctx: moderngl.Context) -> None:
        self.ctx, self.made = ctx, list[Any]()

    def __call__(self, data: np.ndarray) -> Any:
        buf = self.ctx.buffer(np.ascontiguousarray(data).tobytes() or b"\0" * 16)
        self.made.append(buf)
        return buf

    def instances(self, batch: Batch) -> list[tuple[Any, ...]]:
        buffers = (self(batch.rows), self(batch.colors), self(batch.ids))
        return [(buf, fmt, *names) for buf, (fmt, *names) in zip(buffers, INSTANCE_LAYOUT, strict=True)]


class GpuScene:
    """Owns every GL object of one uploaded scene; ``release()`` frees them."""

    def __init__(self, ctx: moderngl.Context, programs: Programs, scene: PreviewScene) -> None:
        self.ctx, self.programs, self.scene = ctx, programs, scene
        self.draws: list[Draw] = []
        self._buf = _Buffers(ctx)
        box = unit_box()
        mesh = [(self._buf(box.interleaved()), "3f 3f", "in_pos", "in_normal")]
        self._box_ibo, self._quad = self._buf(box.indices), [(self._buf(QUAD), "2f", "in_corner")]
        self._quad_ibo = self._buf(QUAD_INDICES)
        with_mesh = lambda b: mesh + self._buf.instances(b)  # noqa: E731
        with_quad = lambda b: self._quad + self._buf.instances(b)  # noqa: E731
        for batch, front in zip(scene.boxes, ("ccw", "cw", None), strict=True):
            self._add("mesh", batch, with_mesh, self._box_ibo, front=front)
        for batch, radius in ((scene.spheres, 0.0), (scene.dots, DOT_RADIUS)):
            self._add("sphere", batch, with_quad, self._quad_ibo, {"u_fixed_radius": radius})
        for batch, mode, edges in ((scene.lines, 0, 1), (scene.grids, 1, 12)):
            self._add("segments", batch, self._buf.instances, None, {"u_mode": mode}, vertices=6 * edges)
        self._add_triangles(scene.triangles)

    def _vaos(self, pipeline: str, passes: tuple[str, ...], content: list[tuple[Any, ...]], ibo: Any) -> dict[str, Any]:
        return {
            p: self.ctx.vertex_array(
                self.programs.variants[(pipeline, PROGRAM_OF[p])],
                content,
                index_buffer=ibo,
                index_element_size=4,
                skip_errors=True,
            )
            for p in passes
        }

    def _add(
        self,
        pipeline: str,
        batch: Batch,
        content: Callable[[Batch], list[tuple[Any, ...]]],
        ibo: Any,
        uniforms: dict[str, Any] | None = None,
        vertices: int = 0,
        front: str | None = None,
    ) -> None:
        for subset, passes in zip(batch.split(), (OPAQUE_PASSES, SEE_THROUGH_PASSES), strict=True):
            if len(subset):
                vaos = self._vaos(pipeline, passes, content(subset), ibo)
                self.draws.append(Draw(vaos, len(subset), vertices, dict(uniforms or {}), front))

    def _add_triangles(self, soup: TriangleSoup) -> None:
        for subset, passes in zip(soup.split(), (OPAQUE_PASSES, SEE_THROUGH_PASSES), strict=True):
            if not len(subset):
                continue
            content = [
                (self._buf(subset.vertices), "3f 3f", "in_pos", "in_normal"),
                (self._buf(subset.colors), "4f1", "in_color"),
                (self._buf(subset.ids), "u", "in_id"),
            ]
            self.draws.append(Draw(self._vaos("triangles", passes, content, None), 1, vertices=3 * len(subset)))

    def has_pass(self, pass_: str) -> bool:
        return any(pass_ in d.vaos for d in self.draws)

    def render(self, pass_: str, set_uniforms: Callable[[Any], None]) -> None:
        """Draw every pipeline that takes part in ``pass_`` ('gbuffer', 'accum', 'reveal' or 'pick')."""
        ctx = self.ctx
        for draw in self.draws:
            vao = draw.vaos.get(pass_)
            if vao is None:
                continue
            if draw.front is None or pass_ != "gbuffer":
                ctx.disable(moderngl.CULL_FACE)
            else:
                ctx.enable(moderngl.CULL_FACE)
                ctx.front_face = draw.front
            set_uniforms(vao.program)
            for name, value in draw.uniforms.items():
                if name in vao.program:
                    vao.program[name].value = value
            if draw.vertices:
                vao.render(moderngl.TRIANGLES, vertices=draw.vertices, instances=draw.instances)
            else:
                vao.render(moderngl.TRIANGLES, instances=draw.instances)
        ctx.disable(moderngl.CULL_FACE)
        ctx.front_face = "ccw"

    def release(self) -> None:
        for draw in self.draws:
            for vao in draw.vaos.values():
                vao.release()
        for buf in self._buf.made:
            buf.release()
        self._buf.made.clear()
        self.draws.clear()
