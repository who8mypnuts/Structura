"""SKL front-end rules: typing, immutability, reserved names, recursion (docs/11 §3)."""

from __future__ import annotations

import pytest

from structura.kernels.skl import Buf, bufset, f32, func, u32, vec3
from structura.kernels.skl.frontend import SklError, compile_module
from structura.kernels.skl.types import F32, U32


@func
def soft_literals(x: u32, y: f32) -> f32:
    a = x * 3 + 1
    return f32(a) * y + 2


@func
def mixes_types(x: u32, y: f32) -> f32:
    return x + y  # type: ignore[operator]


@func
def mutates_vector(v: vec3) -> vec3:
    v.x = 1.0
    return v


@func
def uses_reserved(out: f32) -> f32:
    return out


@func
def ping(x: u32) -> u32:
    return pong(x)


@func
def pong(x: u32) -> u32:
    return ping(x)


def test_soft_integer_literals_adapt() -> None:
    fn = compile_module([soft_literals]).functions["soft_literals"]
    assert dict(fn.params) == {"x": U32, "y": F32} and fn.ret == F32


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        (mixes_types, "share a numeric type"),
        (mutates_vector, "immutable"),
        (uses_reserved, "reserved"),
        (ping, "recursion"),
    ],
)
def test_rejections(entry: object, message: str) -> None:
    with pytest.raises(SklError, match=message):
        compile_module([entry])


@bufset
class Pair:
    left: Buf[f32]
    right: Buf[u32]


@func
def pair_sum(p: Pair, i: u32) -> f32:
    return p.left[i] + f32(p.right[i])


@func
def pair_caller(scale: f32, p: Pair) -> f32:
    return pair_sum(p, u32(0)) * scale


def test_bufsets_expand_to_plain_buffer_parameters() -> None:
    module = compile_module([pair_caller])
    names = [n for n, _ in module.functions["pair_caller"].params]
    assert names == ["scale", "left", "right"]
    assert [n for n, _ in module.functions["pair_sum"].params] == ["left", "right", "i"]
    assert "pair_sum(left, right" in module.functions["pair_caller"].source
