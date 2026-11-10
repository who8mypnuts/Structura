"""Principled BSDF (docs/10 §3.1): Lambert diffuse, GGX dielectric/metal specular, rough dielectric
transmission (Walter et al. 2007) with its own roughness, thin-walled transmission (straight through, no
bending: single-sided panes and shells), and a GGX clear coat layered by Fresnel-weighted albedo scaling. The
specular lobe is anisotropic (Disney's aspect mapping) about a tangent angle given in the local frame.

All directions are in the local frame (z = shading normal, which faces the incoming ray, so wo.z > 0).
``eval`` returns f·|cos θi| together with the one-sample lobe-mixture pdf, so estimators divide directly.
"""

from __future__ import annotations

from structura.kernels.skl import PI, Buf, abs, clamp, cos, dot, f32, func, max, normalize, sin, sqrt, struct, u32, vec3

from .layout import (
    M_ANISO_ROTATION,
    M_ANISOTROPY,
    M_COAT,
    M_COAT_ROUGHNESS,
    M_IOR,
    M_METALLIC,
    M_ROUGHNESS,
    M_SPECULAR,
    M_THIN,
    M_TRANS_ROUGHNESS,
    M_TRANSMISSION,
)
from .microfacet import (
    fresnel_dielectric,
    ggx_alpha,
    ggx_d,
    ggx_d_aniso,
    ggx_g1,
    ggx_g2,
    ggx_lambda_aniso,
    luminance,
    reflect_about,
    refract_about,
    sample_vndf,
    sample_vndf_aniso,
    schlick,
    schlick1,
    vndf_reflect_pdf,
)
from .sampling import cosine_local
from .surface import Surface

ANISO_ASPECT = 0.9  # Disney: aspect = sqrt(1 − 0.9·|anisotropy|)
COAT_F0 = 0.04
INV_PI = 0.3183098861837907


@struct
class Principled:
    base: vec3
    f0: vec3  # specular reflectance at normal incidence (dielectric/metal blend)
    ax: f32  # specular alphas along and across the tangent
    ay: f32
    tc: f32  # the tangent's direction in the local frame: (cos, sin)
    ts: f32
    a_coat: f32
    a_trans: f32  # the glass lobe (transmission_roughness, else roughness)
    eta: f32  # n_t / n_i for the side the ray is on (thin-walled: always from the outside)
    thin: f32  # 1: thin-walled transmission passes straight through
    w_diffuse: f32
    w_spec: f32
    w_glass: f32
    coat: f32
    base_scale: f32  # energy left for the base layer under the coat: 1 − coat·F_coat(wo)
    prob_diffuse: f32  # lobe sampling probabilities (sum to 1)
    prob_spec: f32
    prob_glass: f32


@struct
class BsdfValue:
    f: vec3  # f · |cos θi|
    pdf: f32


@func
def principled_setup(mat_f: Buf[f32], s: Surface, wo: vec3, front: u32, alpha_floor: f32, tangent: f32) -> Principled:
    """Per-hit lobe weights; ``alpha_floor`` regularises glossy lobes (filtered caustics); ``tangent`` is the
    angle of the anisotropy axis in the local frame (surface.tangent_angle)."""
    m = s.mat
    metallic = clamp(mat_f[m + M_METALLIC], 0.0, 1.0)
    ior = mat_f[m + M_IOR]
    glass = clamp(mat_f[m + M_TRANSMISSION], 0.0, 1.0) * (1.0 - metallic)
    r = (ior - 1.0) / (ior + 1.0)
    f0_d = clamp(r * r * mat_f[m + M_SPECULAR] * 2.0, 0.0, 1.0)
    f0 = vec3(f0_d) * (1.0 - metallic) + s.base * metallic
    coat = clamp(mat_f[m + M_COAT], 0.0, 1.0)
    coat_f = coat * schlick1(COAT_F0, wo.z)
    w_diffuse = (1.0 - metallic) * (1.0 - glass)
    w_spec = 1.0 - glass
    e_diffuse = w_diffuse * luminance(s.base) * (1.0 - schlick1(f0_d, wo.z))
    e_spec = w_spec * luminance(schlick(f0, wo.z))
    base_scale = 1.0 - coat_f
    total = max((e_diffuse + e_spec + glass) * base_scale + coat_f, 1.0e-8)
    prob_diffuse = e_diffuse * base_scale / total
    prob_spec = e_spec * base_scale / total
    prob_glass = glass * base_scale / total
    thin = mat_f[m + M_THIN]
    eta = ior if front == u32(1) or thin != 0.0 else 1.0 / ior
    aniso = clamp(mat_f[m + M_ANISOTROPY], -1.0, 1.0)
    aspect = sqrt(1.0 - ANISO_ASPECT * abs(aniso))
    alpha = ggx_alpha(mat_f[m + M_ROUGHNESS])
    along = max(alpha / aspect, alpha_floor)
    across = max(alpha * aspect, alpha_floor)
    angle = tangent + 2.0 * PI * mat_f[m + M_ANISO_ROTATION]
    a_coat = max(ggx_alpha(mat_f[m + M_COAT_ROUGHNESS]), alpha_floor)
    rough_t = mat_f[m + M_TRANS_ROUGHNESS]
    a_trans = max(ggx_alpha(rough_t if rough_t > 0.0 else mat_f[m + M_ROUGHNESS]), alpha_floor)
    return Principled(
        s.base, f0, along if aniso >= 0.0 else across, across if aniso >= 0.0 else along, cos(angle), sin(angle),
        a_coat, a_trans, eta, thin, w_diffuse, w_spec, glass, coat, base_scale, prob_diffuse, prob_spec, prob_glass,
    )  # fmt: skip


@func
def to_tangent(p: Principled, v: vec3) -> vec3:
    """Local-frame v in the anisotropy frame (x along the tangent)."""
    return vec3(p.tc * v.x + p.ts * v.y, p.tc * v.y - p.ts * v.x, v.z)


@func
def from_tangent(p: Principled, v: vec3) -> vec3:
    return vec3(p.tc * v.x - p.ts * v.y, p.ts * v.x + p.tc * v.y, v.z)


@struct
class SpecLobe:
    d: f32  # D(h)
    g2: f32  # G2(wo, wi)
    pdf: f32  # solid-angle pdf of the VNDF-sampled reflection


@func
def spec_lobe(p: Principled, wo: vec3, wi: vec3, h: vec3) -> SpecLobe:
    """The anisotropic specular microfacet terms of the reflection wo → wi about h."""
    lo = ggx_lambda_aniso(to_tangent(p, wo), p.ax, p.ay)
    li = ggx_lambda_aniso(to_tangent(p, wi), p.ax, p.ay)
    d = ggx_d_aniso(to_tangent(p, h), p.ax, p.ay)
    return SpecLobe(d, 1.0 / (1.0 + lo + li), d / ((1.0 + lo) * 4.0 * max(wo.z, 1.0e-6)))


@func
def reflection_value(p: Principled, wo: vec3, wi: vec3) -> BsdfValue:
    h = normalize(wo + wi)
    oh = max(dot(wo, h), 1.0e-6)
    inv4 = 1.0 / (4.0 * max(wo.z, 1.0e-6))
    lobe = spec_lobe(p, wo, wi, h)
    spec = schlick(p.f0, oh) * (lobe.d * lobe.g2 * inv4)
    diffuse = p.base * (INV_PI * wi.z * (1.0 - schlick1(luminance(p.f0), wo.z)))
    fr = fresnel_dielectric(oh, p.eta)
    glass_r = fr * ggx_d(h, p.a_trans) * ggx_g2(wo, wi, p.a_trans) * inv4
    d_c = ggx_d(h, p.a_coat)
    coat = p.coat * schlick1(COAT_F0, oh) * d_c * ggx_g2(wo, wi, p.a_coat) * inv4
    f = (diffuse * p.w_diffuse + spec * p.w_spec + vec3(glass_r * p.w_glass)) * p.base_scale + vec3(coat)
    pdf_coat = vndf_reflect_pdf(wo, h, p.a_coat)
    prob_coat = 1.0 - p.prob_diffuse - p.prob_spec - p.prob_glass
    pdf = (
        p.prob_diffuse * wi.z * INV_PI
        + p.prob_spec * lobe.pdf
        + p.prob_glass * vndf_reflect_pdf(wo, h, p.a_trans) * fr
        + prob_coat * pdf_coat
    )
    return BsdfValue(f, pdf)


@func
def thin_transmission_value(p: Principled, wo: vec3, wi: vec3) -> BsdfValue:
    """Thin-walled glass: the lower-hemisphere mirror image of a glossy reflection, weighted by 1 − Fresnel."""
    wr = vec3(wi.x, wi.y, -wi.z)
    h = normalize(wo + wr)
    oh = max(dot(wo, h), 1.0e-6)
    fr = fresnel_dielectric(oh, p.eta)
    ft = (1.0 - fr) * ggx_d(h, p.a_trans) * ggx_g2(wo, wr, p.a_trans) / (4.0 * max(wo.z, 1.0e-6))
    f = p.base * (ft * p.w_glass * p.base_scale)
    return BsdfValue(f, p.prob_glass * vndf_reflect_pdf(wo, h, p.a_trans) * (1.0 - fr))


@func
def transmission_value(p: Principled, wo: vec3, wi: vec3) -> BsdfValue:
    if p.w_glass <= 0.0:
        return BsdfValue(vec3(0.0), 0.0)
    if p.thin != 0.0:
        return thin_transmission_value(p, wo, wi)
    h = normalize(wo + wi * p.eta)
    if h.z < 0.0:
        h = h * -1.0
    oh = dot(wo, h)
    ih = dot(wi, h)
    if oh <= 0.0 or ih >= 0.0:
        return BsdfValue(vec3(0.0), 0.0)
    fr = fresnel_dielectric(oh, p.eta)
    denom = ih + oh / p.eta
    denom = denom * denom
    d = ggx_d(h, p.a_trans)
    g = ggx_g2(wo, wi, p.a_trans)
    ft = d * g * (1.0 - fr) * abs(ih * oh) / (denom * max(wo.z, 1.0e-6) * p.eta * p.eta)
    f = p.base * (ft * p.w_glass * p.base_scale)
    pdf_h = ggx_g1(wo, p.a_trans) * oh * d / max(wo.z, 1.0e-6)
    return BsdfValue(f, p.prob_glass * pdf_h * abs(ih) / denom * (1.0 - fr))


@func
def bsdf_eval(p: Principled, wo: vec3, wi: vec3) -> BsdfValue:
    """f·|cos θi| and pdf of wi; the zero vector (an invalid sample) has pdf 0."""
    if wi.z > 0.0:
        return reflection_value(p, wo, wi)
    if wi.z < 0.0:
        return transmission_value(p, wo, wi)
    return BsdfValue(vec3(0.0), 0.0)


@func
def upper(w: vec3) -> vec3:
    """w if it lies above the surface, else the invalid zero vector."""
    return w if w.z > 0.0 else vec3(0.0)


@func
def bsdf_sample(p: Principled, wo: vec3, u_lobe: f32, u1: f32, u2: f32) -> vec3:
    """A direction from one lobe (chosen by u_lobe), or the zero vector if the microfacet sample is invalid.

    Evaluate the result with bsdf_eval for the estimator weight.
    """
    if u_lobe < p.prob_diffuse:
        return cosine_local(u1, u2)
    if u_lobe < p.prob_diffuse + p.prob_spec:
        h_spec = from_tangent(p, sample_vndf_aniso(to_tangent(p, wo), p.ax, p.ay, u1, u2))
        return upper(reflect_about(wo, h_spec))
    if u_lobe < p.prob_diffuse + p.prob_spec + p.prob_glass:
        h = sample_vndf(wo, p.a_trans, u1, u2)
        fr = fresnel_dielectric(dot(wo, h), p.eta)
        reuse = (u_lobe - p.prob_diffuse - p.prob_spec) / max(p.prob_glass, 1.0e-8)  # uniform in [0,1) again
        if reuse < fr:
            return upper(reflect_about(wo, h))
        if p.thin != 0.0:  # straight through: the reflection mirrored below the surface
            r = reflect_about(wo, h)
            return vec3(r.x, r.y, -r.z) if r.z > 0.0 else vec3(0.0)
        t = refract_about(wo, h, p.eta)
        return t if t.z < 0.0 else vec3(0.0)
    return upper(reflect_about(wo, sample_vndf(wo, p.a_coat, u1, u2)))
