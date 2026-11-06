"""GUI parameter values and their substitution (docs/05 §2.2).

Structure Synth shows a spin box per GUI parameter: float spin boxes hold 2 decimals, and values are
clamped to [minimum, maximum]. The chosen values (or these defaults) are then substituted over the whole
preprocessed document with the same raw-substring rules as '#define', sharing one 100-hit cap.
"""

from __future__ import annotations

from collections.abc import Mapping

from .preprocessor import GuiParameter, format_number, substitute


def _round2(value: float) -> float:
    return float(f"{value:.2f}")


def default_value(param: GuiParameter) -> float:
    """The value a freshly created GUI control reports."""
    if param.kind == "int":
        top = int(param.maximum)
        bottom = min(int(param.minimum), top)
        return float(min(max(int(param.default), bottom), top))
    high = _round2(param.maximum)
    low = min(_round2(param.minimum), high)
    return min(max(_round2(param.default), low), high)


def value_text(param: GuiParameter, value: float) -> str:
    return str(int(value)) if param.kind == "int" else format_number(value)


def apply_gui_parameters(text: str, params: list[GuiParameter], values: Mapping[str, float] | None = None) -> str:
    table: dict[str, str] = {}
    for param in params:
        chosen = (values or {}).get(param.name)
        value = default_value(param) if chosen is None else chosen
        table[param.name] = value_text(param, value)
    result, _ = substitute(text, table)
    return result
