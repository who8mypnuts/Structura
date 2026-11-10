"""The tiled sampler (docs/09 §5.2, after Sunflow's BucketRenderer with POV-Ray's confidence test): buckets
are rendered one at a time in the chosen order; inside a bucket, passes continue until every pixel reached
the sample count or, with a noise threshold, fell below it. Only the bucket's rows of the film are read
back, into a host copy of the whole film; snapshots are published at most every SNAPSHOT_SECONDS."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator

import numpy as np

from .bands import Bands
from .buckets import Rect, buckets
from .film import active_mask
from .kernels.layout import FILM_F
from .pacing import Pacing
from .progress import RenderProgress, RenderRun

SNAPSHOT_SECONDS = 0.25


def _rows(run: RenderRun, rect: Rect) -> tuple[int, int]:
    w = run.size[0]
    return rect[1] * w * FILM_F, rect[3] * w * FILM_F


def _bucket_film(run: RenderRun, rect: Rect) -> np.ndarray:
    """The bucket's part of the device film, as (rows, W, FILM_F) for its rows."""
    start, stop = _rows(run, rect)
    return run.bound.read_range("accum", start, stop).reshape(rect[3] - rect[1], run.size[0], FILM_F)


def _still_noisy(run: RenderRun, rows: np.ndarray, rect: Rect) -> np.ndarray:
    x0, y0, x1, y1 = rect
    sub = np.ascontiguousarray(rows[:, x0:x1]).ravel()
    return active_mask(sub, x1 - x0, y1 - y0, run.settings.noise_threshold).reshape(y1 - y0, x1 - x0)


def render_bucket(run: RenderRun, rect: Rect, pacing: Pacing, between: Callable[[], None] | None) -> np.ndarray:
    """Sample one bucket to completion (or the time limit); returns its rows of the film."""
    s, (w, h) = run.settings, run.size
    x0, y0, x1, y1 = rect
    mask = run.mask.reshape(h, w)
    local = np.zeros_like(mask)
    local[y0:y1, x0:x1] = mask[y0:y1, x0:x1]
    done = int(run.counts[y0:y1, x0:x1][local[y0:y1, x0:x1] > 0].min())
    bands = Bands(x1 - x0, y1 - y0, origin=(x0, y0))
    run.bound.update(pixel_mask=local.ravel())
    rows = _bucket_film(run, rect)
    while done < s.samples and local.any() and not run.out_of_time():
        spp = pacing.next(done)
        run.bound.update(sample_base=run.sample_base(done), spp=spp)
        pacing.observe(spp, bands.dispatch(run.bound, between))
        done += spp
        run.counts += local.astype(np.int32) * spp
        if s.noise_threshold > 0 and done >= s.adaptive_min_samples:
            rows = _bucket_film(run, rect)
            local[y0:y1, x0:x1] &= _still_noisy(run, rows, rect).astype(np.uint32)
            run.bound.update(pixel_mask=local.ravel())
    mask[y0:y1, x0:x1] = local[y0:y1, x0:x1] if done < s.samples else 0
    return _bucket_film(run, rect)


def tiled_passes(
    run: RenderRun, film: np.ndarray, between: Callable[[], None] | None = None
) -> Iterator[RenderProgress]:
    """Renders bucket by bucket, yielding snapshots as the buckets finish.

    Args:
        run: The bound render.
        film: The host copy of the film (a resumed render starts from its saved film).
        between: Runs between the row bands of each dispatch (cancellation checks).

    Yields:
        The progress after each bucket (or group of buckets), with the next bucket marked.
    """
    s, (w, h) = run.settings, run.size
    order = buckets(w, h, s.bucket_size, s.bucket_order, s.seed)
    todo = [r for r in order if run.mask.reshape(h, w)[r[1] : r[3], r[0] : r[2]].any()]
    pacing, finished, shown = Pacing(s), len(order) - len(todo), time.perf_counter()
    host = film.reshape(h, w, FILM_F)
    for k, rect in enumerate(todo):
        started = time.perf_counter()
        host[rect[1] : rect[3]] = render_bucket(run, rect, pacing, between)
        run.pass_times.append(time.perf_counter() - started)  # per bucket
        finished += 1
        last = k + 1 == len(todo) or run.out_of_time()
        if last or time.perf_counter() - shown >= SNAPSHOT_SECONDS:
            shown = time.perf_counter()
            yield run.snapshot(film, tile=None if last else todo[k + 1], completed=finished / max(1, len(order)))
        if run.out_of_time():
            return
