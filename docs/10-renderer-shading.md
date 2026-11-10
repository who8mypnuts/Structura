# 10 — Renderer Shading: Integrators, Materials, Lights, Cameras

Everything in this document is written as SKL kernels ([11](11-compute-backends.md)). Each item is therefore
implemented once and runs on the GPU and CPU backends.

## 1. Overview

| Component | Registry | Built-ins |
|-----------|----------|-----------|
| Integrators | `render.integrators` | `preview`, `classic`, `ao`, `path`, `photon-caustics` (R3) |
| Material models | `render.materials` | `principled`, `constant`, `wireframe`, `ao`, `debug-*` |
| Material presets | `core/scene/materials.toml` (as built; planned as `render/materials/presets.toml`) | 22 presets (§3.3) |
| Lights | `render.lights` | point, sphere, spot, sun, rect, emissive geometry, env (colour / gradient / HDRI / sun-sky) |
| Cameras | `render.cameras` | perspective (thin lens), orthographic, spherical, fisheye |
| Filters | `render.film.filters` | box, triangle, gaussian, mitchell, catmull-rom, blackman-harris, lanczos, sinc, cubic B-spline |

## 2. Integrators

### 2.1 `classic`: Structure Synth 1.5 internal raytracer (compatibility)

This reproduces `RenderThread::rayCast` so legacy scenes render as users remember them.

| Aspect | Legacy behaviour reproduced |
|--------|-----------------------------|
| Lighting | `light = diffuse·max(0, N·L̂) + spec + ambient·AO` with per-material `legacy_ambient/diffuse/specular` (defaults 0.6/0.6/0.6) |
| Specular | With unnormalised `L`, `d = N·L`. If `d ≥ 0.1`: `r̂ = normalize(2dN − L)`, `s = −r̂·D̂`, and the term is `specular·s⁵⁰` when `s ≥ 0.1` (else 0) |
| Shadows | One hard shadow ray to a point light. Occluders with α < 1 do not cast shadows. In shadow, `light = ambient·AO` |
| AO | First hit only. N×N stratified **uniform** sphere directions flipped into the hemisphere, unweighted, unlimited distance: `AO = 1 − hits/tests` |
| Transparency | `c = c·α + trace_through·(1−α)`, excluding the hit object |
| Reflection | `c = c·(1−r) + trace_reflect·r` |
| Depth | `max-depth` recursion limit (default 5); background colour on a miss |
| Default light | Position = the near-plane unprojection of screen point (−200 px, top edge) at the reference viewport size. It sits up and to the left of the view, exactly as in 1.5. |
| DOF | The legacy model: focus at fraction `center` between the near (5) and far (60) planes; lens offset = `falloff ×` near-plane extent (an elliptical aperture on non-square images) |
| AA | N×N stratified jitter (`samples`, default 6 in window / 8 final) |

**Implementation note (M2).** SKL has no recursion, so the original's two recursive branches
(transparency and reflection) become a stochastic walk. At each hit, the local term
`(1−r)·α·colour·light` is added, then *one* continuation is chosen with probability proportional to its
weight (`(1−r)(1−α)` through, `r` reflected) and the path weight is multiplied by their sum. The expected
value equals the recursive result and converges with the progressive sample count. Secondary rays exclude
the instance they leave, exactly like 1.5's `excludeThis`.

The classic integrator is not physically based, and that is intended. It is the default only when a script
uses `set raytracer::*` and the user picks "Render (legacy look)".

### 2.2 `ao`: Sunflow ambient-occlusion look

This ports Sunflow's `AmbientOcclusionShader` / `AmbientOcclusionGIEngine`. For each camera hit:

```
color = (1/n) Σ_i  blend(bright, dark, occluded(ray_i, maxdist)),  ray_i ~ cosine hemisphere
```

- `bright` defaults to the instance colour and `dark` to black, matching `Sunflow-Colored.rendertemplate`.
- `samples` and `maxdist` are settings.
- Optional direct lighting from declared lights can be added (`ao.direct = true`). *(Built in M11 as
  `ao_direct`: the sun and every declared light, with shadows, over a white Lambertian surface, added to
  the occlusion term.)*
- This is the classic "white studio" Structure Synth look, and it is **cheap** (no recursion).

### 2.3 `path`: unidirectional path tracer (default for final renders)

| Feature | Detail |
|---------|--------|
| Estimator | Next-event estimation + BSDF sampling, combined with **MIS** (power heuristic) |
| Light selection | Power-proportional alias table over all lights and emissive instances; env has its own probability |
| Depth control | Limits for total, diffuse, glossy and transmission bounces (Sunflow `depths.*` generalised); Russian roulette from bounce 3. **M11:** `diffuse_bounces`, `glossy_bounces`, `transmission_bounces` (−1 = only `max_bounces` applies); a bounce is transmission when it crosses the surface, else diffuse-like when its sampled pdf is below 2 (the same test as `caustics filtered`), else glossy |
| Firefly control | Optional clamp of indirect sample luminance |
| Caustics | `caustics = on/off/filtered` (roughness regularisation on secondary bounces). **M2:** `filtered` (the default) raises the GGX alpha of every lobe to ≥ 0.3 after the first rough bounce (sampled pdf < 2), which removes the sun-caustic fireflies from glossy neighbours |
| Opacity | Stochastic pass-through, using instance alpha × material opacity |
| Volumes | Beer–Lambert attenuation inside transmissive materials (`attenuation_color/distance`) |
| Ground | Optional infinite plane or **shadow catcher** under the scene bounds (`render.ground`) |
| Fog | Homogeneous / height-exponential fog with single scattering from the sun or env (R3; POV-Ray `fog` idea) |
| AOVs | First-hit AOVs written on every sample ([09](09-renderer.md) §6) |

### 2.4 `preview`: fast first-hit shading

- `albedo × (hemisphere ambient + key N·L) × AO(4 rays, short distance)`, at 1 spp.
- Used by the **CPU fallback viewport** ([08](08-viewport.md) §9) and by "quick render" thumbnails (variation
  explorer, examples gallery).

### 2.5 `photon-caustics` (phase R3)

- Port of Sunflow's `CausticPhotonMap`: photons are emitted from lights and stored after a specular→diffuse
  path. The gather uses a hashed grid.
- It combines with `path` (caustic paths are then excluded from path tracing).
- The CPU implementation comes first; the GPU version follows once the hash-grid kernel passes parity tests.

## 3. Materials

### 3.1 Principled BSDF (`principled`)

| Lobe | Model |
|------|-------|
| Diffuse | Lambert (Burley retro-reflection optional) |
| Specular (dielectric) | GGX / Trowbridge–Reitz, height-correlated Smith G; Fresnel from `ior` scaled by `specular` (F0 = 0.08·specular) |
| Metal | GGX with F0 = base colour (Schlick, with edge tint = white) |
| Transmission | Rough dielectric BTDF (Walter et al. 2007); thin-walled option for single-sided geometry |
| Clearcoat | GGX with IOR 1.5, `coat` weight, `coat_roughness` |
| Anisotropy | GGX anisotropic (`anisotropy`, `anisotropy_rotation`); the tangent frame comes from the instance's local x axis, which is a natural fit for Structure Synth frames |
| Emission | `emission × emission_strength` (the instance is added to the light list) |
| Sampling | Visible-normal (VNDF) sampling via spherical caps (Dupuy & Benyoub 2023); lobe selection by estimated albedo |

Material fields match [07](07-scene-model.md) §3. That includes `attenuation_color`/`attenuation_distance`
(glass absorption) and `anisotropy`/`anisotropy_rotation` (brushed metal).

### 3.2 Special models

| Model | Purpose | Sunflow origin |
|-------|---------|----------------|
| `constant` | Unlit colour (flat graphic look, emissive "neon" without light contribution) | `ConstantShader` |
| `wireframe` | Edge lines on boxes and triangles (distance-to-edge in object or barycentric space) over a fill colour | `WireframeShader` |
| `ao` | Per-material AO look inside any integrator | `AmbientOcclusionShader` |
| `debug_normal`, `debug_id`, `debug_uv`, `debug_generation`, `debug_gray` (script only; not offered in the Materials panel) | Diagnostic looks | `NormalShader`, `IDShader`, `PrimIDShader`, `UVShader`, `QuickGrayShader` |

### 3.3 Presets (data: `presets.toml`)

`matte`, `plastic`, `glossy`, `clay`, `ceramic`, `rubber`, `metal`, `chrome`, `gold`, `copper`,
`brushed-metal`, `glass`, `frosted-glass`, `tinted-glass`, `mirror`, `emissive`, `neon`, `ao`, `constant`,
`wireframe`, `shiny` (Sunflow shiny), `legacy` (1.5 Phong).

**Sunflow shader → preset mapping** (also used by the `.sc` exporter in reverse):

| Sunflow shader | Structura equivalent |
|----------------|----------------------|
| `diffuse` | `principled(specular=0, roughness=1)` |
| `phong {diff, spec, power}` | `principled(roughness = sqrt(2/(power+2)), specular from spec)` |
| `shiny {diff, refl}` | `principled(coat = refl, coat_roughness = 0)` (Fresnel-weighted mirror over diffuse) |
| `glass {eta, color, absorption}` | `principled(transmission=1, ior=eta, roughness=0, attenuation_*)` |
| `mirror {color}` | `principled(metallic=1, roughness=0, base=color)` |
| `ward` / `anisotropic ward {roughx, roughy}` | `principled(anisotropy, roughness)` via the standard Ward→GGX fit |
| `amb-occ {bright, dark, samples, dist}` | `ao` model |
| `constant`, `wireframe` | Same-named models |
| `uber` | `principled` (diffuse/specular blend) |
| Textured variants | Post-1.0 (procedural textures are a later feature) |

## 4. Lights

| Light | Sampling | Origin |
|-------|----------|--------|
| Point (optional radius → sphere) | Delta, or a cone toward the sphere | Sunflow `PointLight`, `SphereLight` |
| Sphere | Uniform cone by solid angle | Sunflow `SphereLight` |
| Spot | Delta position + smooth cone falloff (`cone`, `blend`) | Sunflow `DirectionalSpotlight`, POV-Ray spotlight |
| Sun (directional + angular diameter) | Cone sampling | Sunflow `SunSkyLight` (sun part) |
| Rect area | Spherical-rectangle solid-angle sampling | POV-Ray `area_light` idea |
| Emissive geometry | Per-instance: sphere by solid angle; box/triangle by area; selection proportional to power | Sunflow `TriangleMeshLight` |
| Environment: colour / gradient | Cosine or uniform | — |
| Environment: HDRI | 2D marginal/conditional CDF importance sampling + MIS | Sunflow `ImageBasedLight` |
| Environment: sun-sky | Preetham model (Sunflow port); Hosek–Wilkie post-1.0 | Sunflow `SunSkyLight` |

Light linking and light groups (POV-Ray) are post-1.0.

## 5. Cameras

| Camera | Parameters | Origin |
|--------|------------|--------|
| Perspective + thin lens | fov, aperture radius, focus distance (auto = target), **polygonal bokeh** (blades, rotation) | Sunflow `ThinLens` |
| Orthographic | Height; optional aperture via a tilted focal plane (post-1.0) | POV-Ray `orthographic` |
| Spherical (equirectangular 360°) | — | Sunflow `SphericalLens`, POV-Ray `spherical` |
| Fisheye | Equidistant, fov up to 360° | Sunflow `FisheyeLens`, POV-Ray `fisheye` |

**Auto-focus:** Alt+click in the viewport sets `focus_distance` from the picked depth ([08](08-viewport.md) §6).

## 6. Legacy mapping

### 6.1 `set raytracer::*` → settings

The key mapping is in [05](05-eisenscript-language.md) §6.3. In addition:

- Legacy `dof [center, falloff]` → thin lens:
  - `focus_distance = (5 + 55·center) / scale`, along the view axis in world units;
  - `aperture_radius = falloff · H_near / scale`, where `H_near = 2·5·tan(fov/2)`.
  - The `classic` integrator keeps the exact elliptical legacy lens. The other integrators use the circular
    equivalent.
- Legacy `light [x,y,z]` → a point light for `classic`. For `path` it becomes a sphere light (radius 0.5% of
  scene size) with intensity matched so that diffuse brightness at the scene centre is comparable.

### 6.2 Legacy Phong parameters → principled (for `path` / `ao`)

| Legacy | Principled |
|--------|------------|
| Base colour | Instance colour (always) |
| `diffuse` d (0.6) | Base colour scaled by `min(1, d/0.6)` |
| `specular` s (0.6) | `specular = 0.5 · s/0.6`; `roughness = 0.2` (≈ Phong exponent 50) |
| `reflection` r | `coat = r`, `coat_roughness = 0` |
| `ambient` a | Ignored (replaced by GI); a warning is shown once if a ≠ 0.6 |

## 7. POV-Ray ideas adopted (reimplemented; no code reuse)

| Idea | Realised as | Phase |
|------|-------------|-------|
| Recursive adaptive AA + jitter | Tiled-adaptive sampler refinement ([09](09-renderer.md) §5.2) | R2 |
| Confidence-based stopping (focal blur `variance`/`confidence`) | Noise-threshold stopping | R2 |
| Orthographic / spherical / fisheye cameras | §5 | R1/R2 |
| Fresnel, metallic and conserve-energy finishes | The principled BSDF (energy-conserving by construction) | R1 |
| Area lights, spotlights | §4 | R2 |
| Atmospheric fog | `path` fog (§2.3) | R3 |
| CSG | Export-time booleans ([15](15-export.md) §3.1); legacy CSG template markers | E2 |
| Mosaic preview, render block patterns | Quarter-res pass 0; bucket orders | R1 (built in M11: `render/mosaic.py`, `render/buckets.py`) |
| Gamma / colour management | The single colour pipeline ([07](07-scene-model.md) §9) | R1 |

## 8. Post-1.0 candidates

Spectral rendering (Sunflow has spectral curves; POV-Ray 3.8 has `spectral.cpp`), heterogeneous media,
subsurface scattering, procedural textures (Perlin; Sunflow `PerlinModifier`), bump/normal modifiers, SDF
primitives (POV-Ray isosurfaces, Julia fractals), light BVH for many emitters, Hosek–Wilkie sky, thin-film
iridescence, render-time CSG, irradiance cache for fast CPU GI, motion blur (Sunflow `MovingMatrix4`),
stereo / ODS spherical cameras.

> **As built (M12, owner review):** transmission exits apply Beer–Lambert absorption from
> `attenuation_color` / `attenuation_distance` (`kernels/volume.py`, path and photon passes); `thin_walled`
> surfaces transmit without refraction; `transmission_roughness` frosts refraction only; anisotropic GGX uses
> a tangent frame from the surface (`anisotropy`, `anisotropy_rotation`); cut-out opacity is honoured by every
> integrator and the AOVs (`kernels/opacity.py`). Material `model`s (constant, wireframe, ao, shadow catcher,
> debug views) are evaluated in `kernels/models.py`.
