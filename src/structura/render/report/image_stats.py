"""Numbers about the finished image: exposure, dynamic range, clipping, colour, and what the camera saw."""

from __future__ import annotations

import math

import numpy as np

from ...core.scene.ir import PrimitiveKind, SceneIR
from ..aovs import Aovs
from .model import Row, Swatch, row

REC709 = np.array([0.2126, 0.7152, 0.0722], np.float32)
BINS = 64
THUMB_SIZE = 640
PALETTE = 8


def thumbnail(display: np.ndarray, size: int = THUMB_SIZE) -> np.ndarray:
    """Nearest-neighbour downscale to at most ``size`` pixels wide (reports embed it)."""
    w = display.shape[1]
    step = max(1, math.ceil(w / size))
    return np.ascontiguousarray(display[::step, ::step])


def histogram(display: np.ndarray) -> np.ndarray:
    """(BINS, 4) counts of R, G, B and luminance of the 8-bit image on a square-root scale (so small bins stay
    visible next to a large background), scaled so the tallest bin is 1."""
    luminance = (display.astype(np.float32) @ REC709).astype(np.uint8)
    channels = [display[..., c].ravel() for c in range(3)] + [luminance.ravel()]
    counts = np.stack([np.bincount(ch // (256 // BINS), minlength=BINS)[:BINS] for ch in channels], axis=1)
    return np.sqrt(counts / max(1, int(counts.max())))


def palette(display: np.ndarray, count: int = PALETTE) -> tuple[Swatch, ...]:
    """The dominant colours: 4-bit-per-channel bins, most populated first, each shown as its mean colour."""
    pixels = display.reshape(-1, 3).astype(np.int64)
    keys = (pixels[:, 0] >> 4) << 8 | (pixels[:, 1] >> 4) << 4 | pixels[:, 2] >> 4
    counts = np.bincount(keys, minlength=4096)
    sums = np.stack([np.bincount(keys, weights=pixels[:, c], minlength=4096) for c in range(3)], axis=1)
    top = np.argsort(counts)[::-1][:count]
    swatches = []
    for key in top[counts[top] > 0]:
        r, g, b = (sums[key] / counts[key]).round().astype(int)
        swatches.append(Swatch(f"#{r:02x}{g:02x}{b:02x}", float(counts[key] / len(pixels))))
    return tuple(swatches)


def _percent(x: float) -> str:
    return f"{100 * x:.2f} %"


def exposure_rows(linear: np.ndarray, display: np.ndarray) -> list[Row]:
    lum = linear.reshape(-1, 3) @ REC709
    lo, median, hi = (float(v) for v in np.percentile(lum, [0.1, 50, 99.9]))
    stops = math.log2(hi / lo) if lo > 1e-6 and hi > lo else float("inf")
    clipped = float((display >= 255).any(axis=-1).mean())
    crushed = float((display <= 2).all(axis=-1).mean())
    mean_rgb = display.reshape(-1, 3).mean(axis=0)
    mean_hex = "#" + "".join(f"{int(c):02x}" for c in mean_rgb.round())
    return [
        row("Mean luminance", float(lum.mean()), f"{lum.mean():.4f}", "linear, scene-referred Rec. 709 luminance"),
        row("Median luminance", median, f"{median:.4f}"),
        row("Peak luminance", float(lum.max()), f"{lum.max():.4f}"),
        row("Dynamic range", stops, f"{stops:.1f} stops" if math.isfinite(stops) else "unbounded (black pixels)",
            "log2 of the 99.9th over the 0.1th luminance percentile"),
        row("Clipped pixels", clipped, _percent(clipped), "any channel at 255 after the view transform"),
        row("Crushed blacks", crushed, _percent(crushed), "every channel ≤ 2 after the view transform"),
        row("Mean display colour", [float(c) for c in mean_rgb], mean_hex),
    ]  # fmt: skip


def sampling_rows(sample_map: np.ndarray | None, target: int) -> list[Row]:
    if sample_map is None or not sample_map.size:
        return []
    spp = sample_map.astype(np.float64)
    early = float((spp < target).mean())
    return [
        row("Samples per pixel (min / mean / max)", [int(spp.min()), float(spp.mean()), int(spp.max())],
            f"{int(spp.min()):,} / {spp.mean():,.1f} / {int(spp.max()):,}"),
        row("Pixels converged early", early, _percent(early), "stopped by the noise threshold before the target"),
        row("Pixel samples", int(spp.sum()), f"{int(spp.sum()):,}", "camera paths traced in total"),
    ]  # fmt: skip


def visibility_rows(aovs: Aovs | None, scene: SceneIR) -> list[Row]:
    """What the camera saw, from the first-hit AOVs: coverage, depth range, visible objects and kinds."""
    if aovs is None:
        return []
    ids = aovs.instance[aovs.instance >= 0]
    visible = np.unique(ids)
    visible = visible[visible < len(scene)]
    depth = aovs.depth[np.isfinite(aovs.depth)]
    kinds = np.unique(scene.kind[visible]) if visible.size else np.zeros(0, np.uint8)
    coverage = float((aovs.instance >= 0).mean())
    rows = [
        row("Coverage", coverage, _percent(coverage), "pixels whose camera ray hits the structure"),
        row("Visible objects", int(visible.size),
            f"{visible.size:,} of {len(scene):,} ({_percent(visible.size / max(1, len(scene)))})",
            "distinct instances seen by at least one pixel"),
        row("Visible kinds", [PrimitiveKind(int(k)).name.lower() for k in kinds],
            ", ".join(PrimitiveKind(int(k)).name.lower() for k in kinds) or "—"),
    ]  # fmt: skip
    if depth.size:
        span = f"{depth.min():.3f} – {depth.max():.3f} world units"
        rows.append(row("Depth range", [float(depth.min()), float(depth.max())], span, "distance of the first hits"))
    if visible.size:
        generations = scene.generation[visible]
        rows.append(row("Visible generations", [int(generations.min()), int(generations.max())],
                        f"{generations.min():,} – {generations.max():,}"))  # fmt: skip
    return rows
