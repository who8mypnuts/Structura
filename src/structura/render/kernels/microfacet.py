"""GGX microfacet and Fresnel building blocks, in the local shading frame (z = normal; docs/10 §3.1).

D uses sin²θ computed from x/y directly, which keeps near-mirror lobes (alpha ≈ 1e-3) accurate in f32.
Visible normals are sampled with spherical caps (Dupuy & Benyoub 2023). The anisotropic forms take one alpha
per local axis (x, y); the isotropic helpers are those with both alphas equal.
"""

from __future__ import annotations

from structura.kernels.skl import PI, clamp, cos, dot, f32, func, max, normalize, sin, sqrt, vec3

ALPHA_MIN = 1.0e-3


@func
def ggx_alpha(roughness: f32) -> f32:
    return max(roughness * roughness, ALPHA_MIN)


@func
def ggx_d(h: vec3, a: f32) -> f32:
    """Trowbridge–Reitz normal distribution (h in the upper hemisphere)."""
    a2 = a * a
    s2 = h.x * h.x + h.y * h.y
    t = s2 + h.z * h.z * a2
    return a2 / (PI * t * t)


@func
def ggx_d_aniso(h: vec3, ax: f32, ay: f32) -> f32:
    """Returns the anisotropic Trowbridge–Reitz distribution D(h).

    1 / (π ax ay (x²/ax² + y²/ay² + z²)²), computed scaled by ax²ay² to stay within f32.

    Args:
        h: The microfacet normal in the tangent frame.
        ax: The roughness alpha along the tangent.
        ay: The roughness alpha across it.
    """
    x = h.x * ay
    y = h.y * ax
    z = h.z * ax * ay
    t = x * x + y * y + z * z
    return ax * ax * ax * ay * ay * ay / (PI * t * t)


@func
def ggx_lambda_aniso(w: vec3, ax: f32, ay: f32) -> f32:
    """Returns Smith's Λ(w) for the anisotropic GGX distribution.

    Args:
        w: The direction in the tangent frame.
        ax: The roughness alpha along the tangent.
        ay: The roughness alpha across it.
    """
    c2 = max(w.z * w.z, 1.0e-12)
    s2 = ax * ax * w.x * w.x + ay * ay * w.y * w.y
    return 0.5 * (sqrt(1.0 + s2 / c2) - 1.0)


@func
def ggx_lambda(w: vec3, a: f32) -> f32:
    """Returns Smith's Λ(w) for the isotropic GGX distribution.

    Args:
        w: The direction in the local frame.
        a: The roughness alpha.
    """
    return ggx_lambda_aniso(w, a, a)


@func
def ggx_g1(w: vec3, a: f32) -> f32:
    return 1.0 / (1.0 + ggx_lambda(w, a))


@func
def ggx_g2(wo: vec3, wi: vec3, a: f32) -> f32:
    """Height-correlated Smith masking-shadowing."""
    return 1.0 / (1.0 + ggx_lambda(wo, a) + ggx_lambda(wi, a))


@func
def sample_vndf_aniso(wo: vec3, ax: f32, ay: f32, u1: f32, u2: f32) -> vec3:
    """Samples a visible microfacet normal for a view direction (anisotropic GGX).

    Args:
        wo: The view direction in the tangent frame (wo.z > 0).
        ax: The roughness alpha along the tangent.
        ay: The roughness alpha across it.
        u1: A uniform random number.
        u2: Another uniform random number.

    Returns:
        The microfacet normal.
    """
    v = normalize(vec3(wo.x * ax, wo.y * ay, wo.z))
    phi = 2.0 * PI * u1
    z = (1.0 - u2) * (1.0 + v.z) - v.z
    st = sqrt(clamp(1.0 - z * z, 0.0, 1.0))
    hs = vec3(st * cos(phi), st * sin(phi), z) + v
    return normalize(vec3(hs.x * ax, hs.y * ay, max(hs.z, 1.0e-7)))


@func
def sample_vndf(wo: vec3, a: f32, u1: f32, u2: f32) -> vec3:
    """Returns a visible microfacet normal of the isotropic GGX distribution.

    Args:
        wo: The view direction in the local frame (wo.z > 0).
        a: The roughness alpha.
        u1: A uniform random number.
        u2: Another uniform random number.
    """
    return sample_vndf_aniso(wo, a, a, u1, u2)


@func
def vndf_reflect_pdf(wo: vec3, h: vec3, a: f32) -> f32:
    """Solid-angle pdf of wi = reflect(wo, h) when h ~ VNDF(wo): G1(wo)·D(h) / (4·wo.z)."""
    return ggx_g1(wo, a) * ggx_d(h, a) / (4.0 * max(wo.z, 1.0e-6))


@func
def schlick(f0: vec3, cos_t: f32) -> vec3:
    m = clamp(1.0 - cos_t, 0.0, 1.0)
    m2 = m * m
    return f0 + (vec3(1.0) - f0) * (m2 * m2 * m)


@func
def schlick1(f0: f32, cos_t: f32) -> f32:
    m = clamp(1.0 - cos_t, 0.0, 1.0)
    m2 = m * m
    return f0 + (1.0 - f0) * (m2 * m2 * m)


@func
def fresnel_dielectric(cos_i: f32, eta: f32) -> f32:
    """Unpolarised Fresnel reflectance; eta = n_t / n_i, cos_i > 0 on the incident side."""
    c = clamp(cos_i, 0.0, 1.0)
    s2t = (1.0 - c * c) / (eta * eta)
    if s2t >= 1.0:
        return 1.0
    ct = sqrt(1.0 - s2t)
    r_par = (eta * c - ct) / (eta * c + ct)
    r_perp = (c - eta * ct) / (c + eta * ct)
    return 0.5 * (r_par * r_par + r_perp * r_perp)


@func
def reflect_about(wo: vec3, h: vec3) -> vec3:
    return h * (2.0 * dot(wo, h)) - wo


@func
def refract_about(wo: vec3, h: vec3, eta: f32) -> vec3:
    """Refracted direction of wo through the microfacet h (eta = n_t / n_i); zero vector on TIR."""
    c = dot(wo, h)
    s2t = max(0.0, 1.0 - c * c) / (eta * eta)
    if s2t >= 1.0:
        return vec3(0.0)
    ct = sqrt(1.0 - s2t)
    return wo * (-1.0 / eta) + h * (c / eta - ct)


@func
def luminance(c: vec3) -> f32:
    return 0.2126 * c.x + 0.7152 * c.y + 0.0722 * c.z
