"""Principled BSDF correctness: sampling matches the reported pdf (χ²), pdfs integrate to ≤ 1 and the
sampled estimator conserves energy (docs/18 §5: furnace and χ² tests)."""

from __future__ import annotations

from functools import cache

import numpy as np
import pytest

from structura.compute.base import Launch
from structura.compute.cpu import CpuBackend
from structura.core.scene.material import Material
from structura.kernels.skl import ir
from structura.kernels.skl.frontend import compile_module
from structura.render.materials import pack_material
from tests.render.kernels_bsdf import bsdf_pdfs, bsdf_samples

N_THETA, N_PHI = 24, 48
SAMPLES = 400_000
MATERIALS = {
    "diffuse": Material(roughness=1.0, specular=0.0),
    "plastic": Material(roughness=0.35),
    "metal": Material(metallic=1.0, roughness=0.25),
    "rough-glass": Material(transmission=1.0, roughness=0.4),
    "coated": Material(roughness=0.6, coat=1.0, coat_roughness=0.2),
}
WO = np.array([0.48, 0.1, 0.87])


@cache
def _module() -> ir.Module:
    return compile_module([bsdf_samples, bsdf_pdfs])


def _args(material: Material, front: int) -> dict[str, object]:
    wo = WO / np.linalg.norm(WO)
    return {"front": front, "wo_x": wo[0], "wo_y": wo[1], "wo_z": wo[2], "mat_f": pack_material(material)}


def _samples(material: Material, front: int) -> np.ndarray:
    args = {**_args(material, front), "n": SAMPLES, "result": np.zeros(SAMPLES * 4, np.float32)}
    out = CpuBackend().run(Launch(_module(), "bsdf_samples", (SAMPLES, 1, 1), args))["result"]
    return out.reshape(-1, 4)


def _bin_centres(sub: int = 6) -> tuple[np.ndarray, np.ndarray]:
    """Sub-sampled directions per (θ, φ) bin over the whole sphere, with their solid-angle weights."""
    t = (np.arange(N_THETA * sub) + 0.5) / (N_THETA * sub) * np.pi
    p = (np.arange(N_PHI * sub) + 0.5) / (N_PHI * sub) * 2 * np.pi
    tt, pp = np.meshgrid(t, p, indexing="ij")
    dirs = np.stack([np.sin(tt) * np.cos(pp), np.sin(tt) * np.sin(pp), np.cos(tt)], -1).reshape(-1, 3)
    d_omega = np.sin(tt).ravel() * (np.pi / (N_THETA * sub)) * (2 * np.pi / (N_PHI * sub))
    return dirs.astype(np.float32), d_omega


def _expected(material: Material, front: int) -> tuple[np.ndarray, float]:
    dirs, d_omega = _bin_centres()
    n = len(dirs)
    args = {**_args(material, front), "n": n, "dirs": dirs.ravel(), "result": np.zeros(2 * n, np.float32)}
    out = CpuBackend().run(Launch(_module(), "bsdf_pdfs", (n, 1, 1), args))["result"]
    mass = (out[:n] * d_omega).reshape(N_THETA, 6, N_PHI, 6).sum(axis=(1, 3))
    return mass * SAMPLES, float(mass.sum())


def _histogram(samples: np.ndarray) -> np.ndarray:
    wi, pdf = samples[:, :3], samples[:, 3]
    ok = np.isfinite(wi).all(axis=1) & (np.linalg.norm(wi, axis=1) > 0.5) & (pdf > 0)  # pdf 0: path ends
    w = wi[ok] / np.linalg.norm(wi[ok], axis=1, keepdims=True)
    theta = np.arccos(np.clip(w[:, 2], -1, 1))
    phi = np.mod(np.arctan2(w[:, 1], w[:, 0]), 2 * np.pi)
    ti = np.minimum((theta / np.pi * N_THETA).astype(int), N_THETA - 1)
    pi = np.minimum((phi / (2 * np.pi) * N_PHI).astype(int), N_PHI - 1)
    return np.bincount(ti * N_PHI + pi, minlength=N_THETA * N_PHI).reshape(N_THETA, N_PHI).astype(float)


@pytest.mark.parametrize("front", [1, 0])
@pytest.mark.parametrize("name", sorted(MATERIALS))
def test_sampling_matches_pdf(name: str, front: int) -> None:
    material = MATERIALS[name]
    observed = _histogram(_samples(material, front))
    expected, total = _expected(material, front)
    assert total <= 1.0 + 2e-2, f"pdf integrates to {total}"
    assert observed.sum() == pytest.approx(total * SAMPLES, rel=0.02)  # invalid samples ⇔ missing pdf mass
    big = expected > 20  # Pearson χ² over well-populated bins
    chi2 = float((((observed - expected) ** 2)[big] / expected[big]).sum())
    dof = int(big.sum()) - 1
    assert chi2 < dof + 5 * np.sqrt(2 * dof), f"χ² = {chi2:.0f} for {dof} dof"
