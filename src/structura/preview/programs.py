"""Compiled GLSL programs of the preview engine, one set per GL context."""

from __future__ import annotations

from typing import Any

import moderngl

from .shader_lib import program_sources


def _program(ctx: moderngl.Context, vertex: str, fragment: str, defines: tuple[str, ...] = ()) -> Any:
    sources = program_sources(vertex, fragment, defines)
    return ctx.program(vertex_shader=sources["vertex_shader"], fragment_shader=sources["fragment_shader"])


FULLSCREEN = ("ssao", "blur", "composite", "copy", "present")  # attribute-less full-screen triangle passes


GEOMETRY = ("mesh", "sphere", "segments", "triangles")
PASSES = {"gbuffer": (), "accum": ("OIT_ACCUM",), "reveal": ("OIT_REVEAL",)}


class Programs:
    def __init__(self, ctx: moderngl.Context) -> None:
        self.variants: dict[tuple[str, str], Any] = {
            (name, pass_): _program(ctx, f"{name}.vert", f"{name}.frag", defines)
            for name in GEOMETRY
            for pass_, defines in PASSES.items()
        }
        self.mesh, self.sphere, self.segments, self.triangles = (self.variants[(n, "gbuffer")] for n in GEOMETRY)
        self.ssao: Any = _program(ctx, "fullscreen.vert", "ssao.frag")
        self.blur: Any = _program(ctx, "fullscreen.vert", "blur.frag")
        self.composite: Any = _program(ctx, "fullscreen.vert", "composite.frag")
        self.copy: Any = _program(ctx, "fullscreen.vert", "copy.frag")
        self.present: Any = _program(ctx, "fullscreen.vert", "present.frag")
        self.fullscreen = {name: ctx.vertex_array(getattr(self, name), []) for name in FULLSCREEN}
