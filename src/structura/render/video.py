"""Video encoding of rendered frames (docs/15 §6): MP4 / WebM through imageio-ffmpeg, GIF through Pillow."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import imageio.v3 as iio
import numpy as np

VIDEO_FORMATS = (".mp4", ".webm", ".gif")


def encode_video(path: Path, frames: Sequence[np.ndarray], fps: float) -> None:
    """``frames``: uint8 (H, W, 3) display images."""
    if path.suffix.lower() == ".gif":
        iio.imwrite(path, list(frames), duration=1000 / fps, loop=0)
    else:
        iio.imwrite(path, list(frames), fps=fps, macro_block_size=1)
