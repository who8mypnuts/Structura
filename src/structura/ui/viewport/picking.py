"""The viewport's CPU picking job (preview/pick.py on the compute lane)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ...core.scene.camera import Camera
from ...core.scene.ir import SceneIR
from ...preview.pick import camera_ray, pick
from ...services.jobs import JobContext


@dataclass(frozen=True)
class PickResult:
    row: int | None
    distance: float | None  # along the view direction (a camera's focus distance)
    focus: bool  # Alt+click: set the focus rather than select


def pick_job(
    scene: SceneIR, camera: Camera, size: tuple[int, int], x: int, y: int, focus: bool
) -> Callable[[JobContext], PickResult]:
    def run(ctx: JobContext) -> PickResult:
        origin, direction = camera_ray(camera, size, x, y)
        hit = pick(scene, origin, direction)
        if hit is None:
            return PickResult(None, None, focus)
        forward = camera.basis[0]
        return PickResult(hit[0], hit[1] * float(direction @ forward), focus)  # depth along the view axis

    return run
