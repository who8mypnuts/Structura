"""Fog (docs/10 §2.3, POV-Ray's 'fog' idea): every path segment of length t is blended towards the fog colour
by its optical depth, with density σ(y) = density · exp(−(y − base) / falloff) (falloff 0: homogeneous).
The integral along a straight segment is analytic, so fog adds no noise. Like POV-Ray's fog it changes
what rays see, not the light that reaches surfaces (shadow rays ignore it)."""

from __future__ import annotations

from structura.kernels.skl import Buf, abs, exp, f32, func, min, vec3

from .camera import cfg3
from .layout import FOG_BASE, FOG_COLOR, FOG_DENSITY, FOG_FALLOFF

FAR = 1.0e30


@func
def optical_depth(cfg: Buf[f32], o: vec3, d: vec3, t: f32) -> f32:
    density = cfg[FOG_DENSITY]
    falloff = cfg[FOG_FALLOFF]
    length = min(t, FAR)
    if falloff <= 0.0:
        return density * length
    b = 1.0 / falloff
    start = density * exp(-b * (o.y - cfg[FOG_BASE]))
    slope = b * d.y
    if abs(slope * length) < 1.0e-4:
        return start * length
    return start * (1.0 - exp(-slope * length)) / slope


@func
def fog_transmittance(cfg: Buf[f32], o: vec3, d: vec3, t: f32) -> f32:
    """exp(−∫σ) along o + s·d for s in [0, t] (1 without fog)."""
    if cfg[FOG_DENSITY] <= 0.0:
        return 1.0
    return exp(-min(optical_depth(cfg, o, d, t), 80.0))


@func
def fog_light(cfg: Buf[f32], o: vec3, d: vec3, t: f32) -> vec3:
    """The fog colour a segment adds: colour × (1 − transmittance)."""
    return cfg3(cfg, FOG_COLOR) * (1.0 - fog_transmittance(cfg, o, d, t))
