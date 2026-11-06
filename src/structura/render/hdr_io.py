"""Reading high-dynamic-range environment images (docs/10 §4): OpenEXR through the OpenEXR bindings and
Radiance RGBE (.hdr) with a small reader (new-style run-length encoding and flat scanlines). Everything is
returned as linear float32 RGB, shape (height, width, 3)."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def read_exr(path: Path) -> np.ndarray:
    import OpenEXR  # noqa: PLC0415 - only needed for EXR environments

    with OpenEXR.File(str(path)) as exr:
        channels = exr.channels()
        if "RGB" in channels:
            rgb = np.asarray(channels["RGB"].pixels, np.float32)
        else:
            rgb = np.stack([np.asarray(channels[c].pixels, np.float32) for c in "RGB"], axis=-1)
    return np.ascontiguousarray(rgb[..., :3])


def _header(data: bytes) -> tuple[int, int, int]:
    """(width, height, offset of the pixel data) of a Radiance file."""
    end = data.find(b"\n\n")
    if not data.startswith((b"#?RADIANCE", b"#?RGBE")) or end < 0:
        raise ValueError("not a Radiance HDR file")
    line_end = data.find(b"\n", end + 2)
    axes = data[end + 2 : line_end].decode("ascii").split()  # "-Y height +X width"
    if len(axes) != 4 or axes[0] != "-Y" or axes[2] != "+X":
        raise ValueError(f"unsupported HDR orientation {' '.join(axes)}")
    return int(axes[3]), int(axes[1]), line_end + 1


def _scanline(data: bytes, at: int, width: int) -> tuple[np.ndarray, int]:
    """One scanline of RGBE bytes (width, 4) and the offset after it."""
    if width < 8 or width > 0x7FFF or data[at : at + 2] != b"\x02\x02":
        flat = np.frombuffer(data, np.uint8, width * 4, at).reshape(width, 4)
        return flat, at + width * 4
    at += 4
    line = np.empty((4, width), np.uint8)
    for channel in range(4):
        x = 0
        while x < width:
            count = data[at]
            at += 1
            if count > 128:  # a run
                line[channel, x : x + count - 128] = data[at]
                at, x = at + 1, x + count - 128
            else:
                line[channel, x : x + count] = np.frombuffer(data, np.uint8, count, at)
                at, x = at + count, x + count
    return line.T, at


def read_hdr(path: Path) -> np.ndarray:
    data = path.read_bytes()
    width, height, at = _header(data)
    rgbe = np.empty((height, width, 4), np.uint8)
    for y in range(height):
        rgbe[y], at = _scanline(data, at, width)
    scale = np.where(rgbe[..., 3] > 0, np.ldexp(1.0, rgbe[..., 3].astype(np.int32) - 136), 0.0)
    return (rgbe[..., :3] * scale[..., None]).astype(np.float32)


def write_hdr(path: Path, rgb: np.ndarray) -> None:
    """Flat (uncompressed) RGBE, for tests and baked skies."""
    rgb = np.asarray(rgb, np.float64)
    peak = rgb.max(axis=-1)
    mantissa, exponent = np.frexp(peak)
    scale = np.where(peak > 1e-32, mantissa * 256.0 / np.maximum(peak, 1e-32), 0.0)
    rgbe = np.zeros((*rgb.shape[:2], 4), np.uint8)
    rgbe[..., :3] = np.clip(rgb * scale[..., None], 0, 255).astype(np.uint8)
    rgbe[..., 3] = np.where(peak > 1e-32, exponent + 128, 0).astype(np.uint8)
    header = f"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y {rgb.shape[0]} +X {rgb.shape[1]}\n".encode()
    path.write_bytes(header + rgbe.tobytes())


def read_environment(path: Path) -> np.ndarray:
    suffix = path.suffix.lower()
    if suffix == ".exr":
        return read_exr(path)
    if suffix in (".hdr", ".pic", ".rgbe"):
        return read_hdr(path)
    raise ValueError(f"unsupported environment image '{path.suffix}' (use .exr or .hdr)")
