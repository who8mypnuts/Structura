"""Render targets of the preview frame graph (docs/08 §5): G-buffer, half-resolution AO, shadow map."""

from __future__ import annotations

from typing import Any

import moderngl

SHADOW_SIZE = 2048


def _texture(ctx: moderngl.Context, size: tuple[int, int], components: int, dtype: str) -> Any:
    tex = ctx.texture(size, components, dtype=dtype)
    tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    tex.repeat_x = tex.repeat_y = False
    return tex


class Targets:
    def __init__(self, ctx: moderngl.Context, width: int, height: int) -> None:
        self.size = (max(1, width), max(1, height))
        w, h = self.size
        self.albedo = _texture(ctx, self.size, 4, "f2")
        self.normal = _texture(ctx, self.size, 4, "f2")
        self.ids = _texture(ctx, self.size, 1, "u4")
        self.pick = _texture(ctx, self.size, 1, "u4")
        self.depth = ctx.depth_texture(self.size)
        self.depth.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.gbuffer = ctx.framebuffer([self.albedo, self.normal, self.ids, self.pick], self.depth)
        half = (max(1, w // 2), max(1, h // 2))
        self.ao = [_texture(ctx, half, 1, "f1") for _ in range(2)]
        for tex in self.ao:
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.ao_fbo = [ctx.framebuffer([tex]) for tex in self.ao]
        self.frame = _texture(ctx, self.size, 4, "f2")  # lit frame (linear)
        self.accum = _texture(ctx, self.size, 4, "f4")  # sum of jittered frames
        self.frame_fbo, self.accum_fbo = ctx.framebuffer([self.frame]), ctx.framebuffer([self.accum])
        self.oit_accum = _texture(ctx, self.size, 4, "f2")  # weighted premultiplied colour, weight
        self.oit_reveal = _texture(ctx, self.size, 4, "f2")  # Π(1 − α) in every channel
        self.oit_accum_fbo = ctx.framebuffer([self.oit_accum], self.depth)  # tests against opaque depth
        self.oit_reveal_fbo = ctx.framebuffer([self.oit_reveal], self.depth)
        self._objects = [
            self.albedo, self.normal, self.ids, self.pick, self.depth, self.gbuffer, *self.ao, *self.ao_fbo,
            self.frame, self.accum, self.frame_fbo, self.accum_fbo,
            self.oit_accum, self.oit_reveal, self.oit_accum_fbo, self.oit_reveal_fbo,
        ]  # fmt: skip

    def release(self) -> None:
        for obj in self._objects:
            obj.release()


class ShadowTarget:
    def __init__(self, ctx: moderngl.Context, size: int = SHADOW_SIZE) -> None:
        self.depth = ctx.depth_texture((size, size))
        self.depth.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.depth.repeat_x = self.depth.repeat_y = False
        self.fbo = ctx.framebuffer(depth_attachment=self.depth)

    def release(self) -> None:
        self.fbo.release()
        self.depth.release()
