"""The mosaic first image (docs/09 §5.1, POV-Ray's mosaic preview): one sample in every STEP-th pixel of every
STEP-th row, shown as blocks, so the first picture of a big render arrives at a fraction of a pass's cost.
The film is cleared afterwards: the mosaic's samples do not count, so the render equals one without it."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .bands import Bands
from .film import film_image, new_film
from .progress import RenderProgress, RenderRun

STEP = 4


def mosaic_pass(run: RenderRun, between: Callable[[], None] | None = None) -> RenderProgress:
    w, h = run.size
    mask = np.zeros((h, w), np.uint32)
    mask[::STEP, ::STEP] = run.mask.reshape(h, w)[::STEP, ::STEP]
    run.bound.update(pixel_mask=mask.ravel(), sample_base=run.sample_base(0), spp=1)
    Bands(w, h).dispatch(run.bound, between)
    coarse = film_image(run.bound.read("accum"), w, h)[::STEP, ::STEP]
    image = np.repeat(np.repeat(coarse, STEP, axis=0), STEP, axis=1)[:h, :w]
    run.bound.update(accum=new_film(w, h), pixel_mask=run.mask)
    return RenderProgress(np.ascontiguousarray(image), 0, run.seconds, run.aovs)
