"""Region re-renders and progress estimates for the Render view (docs/09 §9)."""

from __future__ import annotations

from dataclasses import replace

from ...render.settings import RenderSettings
from ...services.render import RenderUpdate


def merge_base(
    last: RenderUpdate | None, settings: RenderSettings, region: tuple[int, ...] | None
) -> RenderUpdate | None:
    """The result a region render is pasted into: the last finished image, if it has the same size."""
    if region is None or last is None:
        return None
    h, w = last.progress.image.shape[:2]
    return last if (w, h) == (settings.width, settings.height) else None


def merged(base: RenderUpdate | None, update: RenderUpdate) -> RenderUpdate:
    """``update`` with its region pasted over ``base``'s image (the region is where it has samples)."""
    if base is None or update.progress.sample_map is None:
        return update
    image = base.progress.image.copy()
    inside = update.progress.sample_map > 0
    image[inside] = update.progress.image[inside]
    image.flags.writeable = False
    return replace(update, progress=replace(update.progress, image=image), display=None, display_for=None)


def eta(update: RenderUpdate) -> str:
    """' · 12 s left' from the rate so far ('' when finished or too early to tell)."""
    p = update.progress
    if p.samples <= 0 or p.samples >= update.total_samples or p.seconds < 0.5:
        return ""
    left = p.seconds / p.samples * (update.total_samples - p.samples)
    return f" · {left:.0f} s left"
