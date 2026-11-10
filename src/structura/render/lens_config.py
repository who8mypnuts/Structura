"""The camera's lens in the render configuration buffer (layout: render/kernels/layout.py; PLAN Q5).

Everything the kernels need is precomputed here: the effective aperture radius and focus distance, the focus
plane's normal (the view direction turned by the lens tilt), the bokeh sampling exponent and the projection."""

from __future__ import annotations

import math

import numpy as np

from ..core.scene.camera import Camera
from ..core.scene.lens import FISHEYE_MAPPINGS
from .kernels import layout as lay

BIAS_RANGE = 1.5  # the sampling exponent is 0.5 · 2^(−bias · BIAS_RANGE): 0.18 (rims) … 1.41 (soft centre)


def bokeh_exponent(bias: float) -> float:
    """Returns the exponent e of the lens sample radius r = u^e (0.5 lights the disc evenly).

    Args:
        bias: The lens's bokeh bias, −1 (soft centre) … 1 (bright rims); clamped.
    """
    return float(0.5 * 2.0 ** (-min(max(bias, -1.0), 1.0) * BIAS_RANGE))


def put_lens(cfg: np.ndarray, camera: Camera) -> None:
    """Writes the lens of a camera into the render configuration.

    Args:
        cfg: The configuration buffer (kernels/layout.py), changed in place.
        camera: The camera (its aperture and focus are resolved here, once).
    """
    lens = camera.lens
    cfg[lay.CAM_TYPE] = lay.CAMERA_TYPES.get(lens.projection, 0)
    cfg[lay.ORTHO_HALF], cfg[lay.FISHEYE_FOV] = lens.ortho_height / 2, math.radians(lens.fisheye_fov_deg)
    mapping = lens.fisheye_mapping
    cfg[lay.FISHEYE_MAP] = FISHEYE_MAPPINGS.index(mapping) if mapping in FISHEYE_MAPPINGS else 0
    cfg[lay.APERTURE], cfg[lay.FOCUS] = camera.aperture_radius, camera.focus
    cfg[lay.BLADES], cfg[lay.BLADE_ROT] = lens.blades, math.radians(lens.blade_rotation_deg)
    cfg[lay.SHIFT : lay.SHIFT + 2] = lens.shift
    cfg[lay.FOCUS_NORMAL : lay.FOCUS_NORMAL + 3] = camera.focus_normal
    cfg[lay.BOKEH_BIAS], cfg[lay.ANAMORPHIC] = bokeh_exponent(lens.bokeh_bias), max(lens.anamorphic, 1e-3)
