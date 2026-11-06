"""Structure Synth's HSV → RGB conversion (docs/05-eisenscript-language.md §4.3).

Hue h is in degrees, s and v in [0, 1]. The sector is i = floor(h / 60) mod 6 (truncation toward zero,
so the legacy hue -1 of achromatic colours maps to sector 0), f = h/60 - i, and

    p = v(1 - s),  q = v(1 - f s),  t = v(1 - (1 - f) s)
    (r, g, b) = [(v,t,p), (q,v,p), (p,v,t), (p,q,v), (t,p,v), (v,p,q)][i]

A hue ≥ 360 is first reduced by 360 once.
"""

from __future__ import annotations

from structura.core.jit import kernel


@kernel
def hsv_to_rgb(h: float, s: float, v: float) -> tuple[float, float, float]:
    if h >= 360.0:
        h -= 360.0
    i = int(h / 60.0) % 6
    f = h / 60.0 - int(h / 60.0)
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    if i == 0:
        return v, t, p
    if i == 1:
        return q, v, p
    if i == 2:
        return p, v, t
    if i == 3:
        return p, q, v
    if i == 4:
        return t, p, v
    return v, p, q
