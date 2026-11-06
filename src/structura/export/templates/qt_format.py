"""Number formatting exactly like Qt 5's QString::number(double) / QString::arg(double).

Both use the 'g' format with 6 significant digits. Unlike C's printf, Qt rounds an exact decimal tie away
from zero (0.2890625 → "0.289063", printf gives "0.289062"), so the exact binary value is rounded with
ROUND_HALF_UP and then laid out like %g. Qt also prints negative zero as "0".
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

PRECISION = 6


def qnum(value: float) -> str:
    """float32 values are widened to double first, exactly as Qt does for Vector3f components."""
    x = float(value)
    if x == 0.0:
        return "0"  # Qt decides the sign with d < 0, so negative zero prints without one
    seven = f"{x:.6e}"  # 7 significant digits: a tie at 6 digits is exactly "…5" with nothing after it
    if seven[seven.index("e") - 1] != "5" or float(seven) != x or not math.isfinite(x):
        return f"{x:g}"  # no tie: printf's rounding is Qt's rounding
    return _tie(x)


def _tie(x: float) -> str:
    d = Decimal(x)
    exponent = d.adjusted()  # position of the leading digit
    quantum = Decimal(1).scaleb(exponent - PRECISION + 1)
    rounded = d.quantize(quantum, rounding=ROUND_HALF_UP)
    if rounded.adjusted() != exponent:  # 9.999995 → 10.0000: the exponent moved up
        exponent = rounded.adjusted()
    if exponent < -4 or exponent >= PRECISION:
        digits = f"{rounded:.{PRECISION - 1}e}"  # exact: Decimal formatting does not re-round
        mantissa, _, exp = digits.partition("e")
        mantissa = mantissa.rstrip("0").rstrip(".") if "." in mantissa else mantissa
        sign, magnitude = ("-" if exp.startswith("-") else "+"), exp.lstrip("+-").lstrip("0") or "0"
        return f"{mantissa}e{sign}{magnitude.zfill(2)}"
    text = f"{rounded:f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def qint(value: int) -> str:
    return str(int(value))
