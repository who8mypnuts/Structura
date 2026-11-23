# Medusarium — Procedural Creature Generation for Structura

**Created:** 2026-11-13  
**Status:** Planning (not yet implemented)  
**Author:** Assistant

---

## 1. Executive summary

Medusarium is a new left-side activity-rail panel that brings **Cindermedusae**—Marcin Ignac's procedural generative artwork of imaginary sea creatures—into Structura as a first-class citizen. It provides:

- A parameterized wireframe and solid creature generator (heads, tentacles, hair)
- Artist-selected morphological controls with live preview
- Organic-looking materials and Haeckel-inspired hatching shading
- Multi-species animation and continuous morphing
- Full integration with Structura's rendering, export, and timeline systems

The tab will not duplicate existing functionality; it reuses Structura's builder, SceneIR, render pipelines, and parameter UI infrastructure.

---

## 2. What already exists (must reuse)

| Capability | Where in Structura | Reuse strategy |
|---|---|---|
| **EisenScript v1/v2** | `core.lang` | Extend with creature rules; use existing parser/compiler |
| **SceneIR struct-of-arrays** | `core.scene` | Creatures are just primitives; no new scene model needed |
| **Builder engine (Numba)** | `core.build` | Rule expansion into vertices, normals, indices |
| **Preview engine** | `preview` | Live viewport with streaming builds and picking |
| **Precision renderer** | `render` | Path tracing / raster for solids (no subsurface scattering exists yet — see §5.1) |
| **Materials system** | `core.scene.material`, `ui/panels/materials.py` | Tag-based selection; add creature tags |
| **Lighting (lights, env, sun)** | `core.scene.light_*` | Add creature-specific light rigs and presets |
| **Parameter UI** | `ui/panels/parameters.py` | ParamForm generates forms from ParamSpec; register new creature params |
| **Timeline & animation** | `core.animation` (timeline in `core/animation/timeline.py`), `ui/workspaces.py` + `ui/panels/variations.py` | Keyframe existing scene parameters; add morph controls |
| **Export pipeline** | `export/mesh/*`, `export/scenes/*` | Creatures export as OBJ/STL/GLTF/USD with provenance |

---

## 3. What is new (Medusarium-specific)

### 3.1 Procedural geometry rules

The creator's making-of article describes a six-step pipeline:

```
#version 2
#param radius float = 1.0 range 0.5..4.0
#param tentacle_count int = 6 range 2..32
#param tentacle_length float = 1.5 range 0.3..8.0
#param tentacle_radius_ratio float = 0.6 range 0.1..1.0
#param head_dome_float float = 0.4 range 0.1..1.0

head {
    radius(radius) * (1 + sin(10*phi) * 0.075)   # radial modulation
    profile(head_dome_float)                       # convex/concave dome
    normals()                                       # surface normals for shading
    emit attachment_sites                         # joints for tentacles
}

tentacle {
    curve(tentacle_count, tentacle_length, radius_ratio)  # polylines → tubes
    taper(tendril_end_pos)                               # reduce at tip
    bend(weight=0.3)                                     # curvature variation
}

hair {
    from attachment_sites(head)                         # share head joints
    count(rand(20, 150))                                 # per-creature variability
    length(rand(0.5, 5))                                 # variable hair lengths
}
```

> The block above is **pseudo-code** describing the intended creature rule templates — not literal EisenScript. `head`/`tentacle`/`hair` are ordinary v2 *rules* (recursive grammar, §3.1 below), not new catalog blocks; randomness comes from the seeded preprocessor stream (`set seed initial`, `random[a,b]`, `color random`) — `rand(a, b)` is *not* an evaluable expression function (`expressions.py` rejects it), and `count(...)`/`emit ...` are not language constructs.

**Implementation plan — creatures are v2 EisenScript, not new geometry code:**

The v2 language already expresses the entire creature model — this is the Structure Synth mechanism the builder is built on, and it means **no new Python geometry is required for the creatures themselves**:

- **Radial symmetry** — the `N * { transform } NAME` loop (loop count is a compile-time expression, so `#param`-driven): `(tentacles) * { ry (360/tentacles) … } tentacle`.
- **Tentacles / chains** — a depth-limited recursive rule with a retirement rule: `rule tentacle md (segments) > tip { { s 0.07 1 0.07 } box::tent { y 0.94 s (taper) rz (bend) } tentacle }`. Each application emits one unit segment and a scaled, bent child — a tapered, swaying chain.
- **Organic variation** — the existing seeded random stream (`set seed initial`, `random[a,b]` / `color random`) plus ambiguous (weighted) rule alternatives, picked per application. No new noise library.
- **Morphing / wobble** — `time`, `frame`, `fps` are bound per frame by the timeline, so a transform term like `rz (sin(time * 30) * 4)` animates the geometry; static builds bind `time = 0`.
- **Head / bell** — a scaled `ellipsoid` (flattened dome) or a `torus` rim + `sphere`; the exact Cindermedusae radial modulation (`1 + 0.075·cos(10φ)`) is a cosmetic detail the language can approximate but does not need.

> **Verified against the builder (2026-11-15/16):** two probe scripts built cleanly with `structura build`. A minimal one (`#param n int`, `(n) * { ry (360/n) … } arm` loop, `arm md (depth) > tip` chain): 105 objects, no errors. A full medusa-style one (ellipsoid bell + torus rim, three ambiguous weighted recursive chains with retirement rules, `material`/`light`/`environment`/`camera`/`render` blocks, 9 `#param`s): **705 objects, 31 generations, zero warnings**. Param-driven loop counts, param-driven `md` depth, weighted ambiguous rules, and `(expr)` transforms all work today. **Randomize (M2) is already supported**: the same script with different `--seed` values produces different geometry (verified by SceneIR hash). Two catalog gotchas noted: material colour is the `base` key (not `color`), and a point light takes `power`, not `intensity`.

**Deliverables:**
- A pre-filled `.es` script per species in `resources/examples/creatures/` (`medusa.es` for M1; the M4 roster in §6.4) — each is a parameter set over shared rule templates.
- Shared rule templates (bell, tentacle chain, hair, spine lattice, spiral whorl, zooid chain, striae valve) reused across species, either as repeated v2 blocks or a small `#include`-style convention.
- **Only if** a shape cannot be expressed in the language (none found so far) does a `core/geometry/creature/` Python module get added — that is a fallback, not the plan.

### 3.2 Morphology parameter panel

The existing Parameters panel (`ui/panels/parameters.py`) already generates forms from ParamSpecs. Medusarium introduces **three new param groups**:

| Group | Controls (ParamSpec) | Default range |
|---|---|---|
| **Head** | `radius`, `dome_float` | 0.5–4.0, 0.1–1.0 |
| **Tentacles** | `count`, `length`, `radius_ratio`, `curvature_weight`, `bend_taper` | 2–32, 0.3–8.0, etc. |
| **Hair** | `count`, `length_range_min/max`, `spread_angle` | 20–150, 0.5–5.0, 10°–90° |

Each parameter has:
- A live preview via the preview engine (streaming build)
- Keyframe support for animation (`key_toggled` in ParametersPanel already wires to Timeline)
- Per-parameter reset-to-default and randomize-within-range buttons

### 3.3 Solid vs wireframe render toggle

The viewport widget (`ui/viewport/host.py`) currently renders SceneIR primitives as colored triangles. Medusarium adds:

| Mode | Rendering pass | Performance note |
|---|---|---|
| **Wireframe** | `model wireframe` — an existing v2 material model (catalog values: `principled \| constant \| wireframe \| ao \| debug_*`) | No normals needed; fast; good for iteration |
| **Solid** | Full PBR pipeline (diffuse + specular) via precision engine or preview shader | Uses existing material/normal/UV systems |

The toggle is a radio button in the Render Settings panel wired to a material-model switch (wireframe vs principled). Wireframe is a **material model in the v2 catalog**, not a separate preview-engine pass — no new renderer work is needed for the toggle itself.

### 3.4 Hatching and illustration shading

Cindermedusae's signature look comes from **diffuse-light-controlled stripe density**:

```
stripe_density = f(diffuse_intensity)
    = clamp(a * diffuse + b, min_stripe, max_stripe)
stripe_width    = noise(tex_coords) * stripe_base_width
```

**Implementation:**
- A new hatch pass (`render/kernels/hatch.py`, registered alongside the existing integrators in `render/kernels/integrators.py` — there is no `render/integrators/` directory) that:
  1. Runs a standard diffuse light pass to get per-pixel illumination
  2. Applies a sinusoidal/herringbone texture based on `dFdx/dFdy` direction (as in the original article's derivative-based explanation)
  3. Samples noise for stripe width modulation
  4. Composites with the base color and ambient occlusion pass

This is **not** a general-purpose painting tool—it's a single procedural hatching pass that produces the natural-history illustration look. It reuses:
- The existing render lighting pipeline — the precision renderer (`render/`) is a **Sunflow-derived** physically based renderer (docs/09-renderer.md: path tracing, NEE/MIS light sampling, QMC sequences), so the hatch pass composites over genuine Sunflow-derived illumination. (`export/scene/text/sunflow.sc.j2` is a separate export template for the `.sc` format.)
- A new small noise module (e.g. `core/geometry/noise.py` with value/Perlin noise) — the repo has **no** Perlin/Simplex library; `core/rng/` is an MT19937 PRNG and `planning/mathmod-13.0-source/` is a reference copy, not a runtime dependency
- The film compositing stage (`render/film.py`, additive layer blending)

### 3.5 Five-layer composition

The making-of article describes a five-layer output pipeline:

```
Layer 1: Yellow background (warm paper tone, base color from theme palette)
Layer 2: Page-corner dirt (noise-masked orange/sepia at edges; controlled by "border" param)
Layer 3: Black sketchy hatch (procedural line density over the creature silhouette)
Layer 4: Blue highlights (cool accent pass masked to surface normals, simulating ink wash)
Layer 5: Pink borders (colored outline around each creature on the page)
```

**Implementation:**
- These are **post-processing layers**, not separate scene objects.
- The composition runs in the precision renderer as a final film pass after geometry/illumination:
  - Background layer: uniform color + vignette
  - Corner dirt: radial gradient + noise
  - Hatch pass: stripe density modulated by diffuse intensity (the main "hatching" effect)
  - Highlights: blue tint weighted by surface normal dot light, masked to silhouette
  - Borders: stroke around each creature's bounding box

All five layers are composable via the existing `render/api` film compositing API. No new export format is needed—this produces a single PNG/EXR with all layers baked in.

### 3.6 Species morphing and animation

Cindermedusae creatures can smoothly transition between forms by animating continuous parameters. In Structura this is expressed with the **existing timeline**, which keys `param:NAME` targets over time (there is no `@animate` block in the language):

```
#version 2
#param radius float = 1.0 range 0.5..4.0
#param tentacle_count int = 6 range 2..32
```

```
# Timeline (keyframes on param targets), e.g. species A → B over 5 s:
#   t=0.0   radius 1.0 | tentacle_count 6  | hair_count 40   (Species A)
#   t=5.0   radius 3.5 | tentacle_count 18 | hair_count 90   (Species B)
```

**Implementation:**
- The existing timeline (`core/animation/timeline.py`) supports keyed parameter values — no language extension is needed for morphing.
- Medusarium adds a **morph preset system**: save two creature configurations as "Species A" and "Species B"; the timeline interpolates all continuous parameters linearly (with easing). Discrete params (count) snap at each frame using `round()`.
- Animation plays in the Render view with progressive rendering; video export is already supported (`structura animate --video`, encoded by `render/video.py`).

---

## 4. File structure (new and modified modules)

### New files

The creature bodies are **v2 EisenScript** (§3.1), so the new artifacts are mostly one parameterized script per species plus a single render post-pass — no new geometry package is required:

```
resources/examples/creatures/          # one parameterized v2 script per species
    medusa.es              # M1 — bell + tentacles + oral arms + fringe
    radiolaria.es          # M4 — see §6.4
    hydra.es               # M4
    shell.es               # M4 (gastropod + bivalve)
    siphonophore.es        # M4
    ctenophore.es          # M4
    urchin.es              # M4
    sand_dollar.es         # M4
    nautilus.es            # M4
    diatom.es              # M4

src/structura/render/kernels/
    hatch.py             # Hatching pass: diffuse-driven stripe density + noise width
                         # (integrators live in render/kernels/integrators.py)

src/structura/core/geometry/
    noise.py             # Small value/Perlin noise for the hatch pass (repo has no noise library)

resources/presets/
    medusa_presets.toml  # Preset render settings (camera, integrator, film compositing)
                         # (NOT export/presets/ — export/presets.py is an existing module)

docs/user-guide/creatures.md       # User guide addition
```

**Fallback only** (if some shape cannot be expressed in v2 — none found so far): a `core/geometry/creature/` package with mesh generators (`head.py`, `tentacle.py`, `hair.py`, and the M4 primitives `spine_lattice.py`, `spiral_whorl.py`, `zooid_chain.py`, `striae_valve.py`). This is a contingency, not the plan.

### Modified files (existing, no duplication)

| File | Change | Why |
|---|---|---|
| `ui/panels/parameters.py` | Add "Species" tab with morph presets | Reuses ParamForm; new params defined in `.es` |
| `ui/panels/render_settings.py` + `ui/render_view/presets.py` | Wireframe/solid toggle switch | Switches the material model (`wireframe` vs `principled`) via existing preset machinery |
| `core/scene/light_rigs.py` + `core/scene/light_rigs.toml` | New creature light rig presets (`creatures/`) | Reuses existing light model; new parameters for rim/hatch lighting |

> **The builder, SceneIR, and preview are untouched by creature geometry.** Creatures are ordinary v2 rules; the existing Numba builder expands them to SceneIR exactly as it does the community corpus (`pytree3drandFlip.es`, `flowertree.es`). No new rule group, no new scene model, no new preview path — verified with a probe build (§3.1). The only new *code* is the hatch pass (§3.4) and the film layers (§3.5); everything else is scripts, presets, and existing UI.

---

## 5. Integration with existing features

### 5.1 Materials — reuse, don't duplicate

Structura already has:
- Tag-based material selection (`box::shiny`, `mat/golden`)
- Principled BSDF controls (albedo, roughness, metallic, normal map)

> **Subsurface scattering is not implemented** in `render/` — it is treated as optional post-M3 work (see §8), not part of the reuse baseline.

**Medusarium reuses:**
- The same tag system; creature primitives get tags like `creature/head::pink`, `creature/tentacle::blue`
- Material assignment is the same: click a primitive in the viewport, open Materials panel, pick a preset or edit params
- No new material pipeline needed—only new **default presets** and **scene-level tag overrides**

### 5.2 Lighting — reuse existing lights + new presets

Cindermedusae creatures look best under warm rim lighting with soft shadows:

| Light type | How to set up in Medusarium |
|---|---|
| Main fill | `light fill { type sphere position [-3 -1 0] radius 4 power 400 color #fff2e0 }` (warm white) |
| Rim light | `light rim { type point position [2 3 2] power 300 color #bcd8ff }` (cool blue for rim effect) |
| Background | `environment { type color color #f5eddc }` (warm paper tone; no sun light, so no sun-sky) |

> Light-block spec (`v2_blocks.toml`): `type` is `sun | point | sphere | spot | rect`; `position`+`power` apply to point/sphere/spot/rect, `radius` to sphere, and `intensity`/`direction`/`angle` to sun only — so a point light takes `power`, not `intensity`.

A one-click **"Creature Lighting Rig"** action sets all these up. It's just the existing `light`/`environment` block syntax in the script (or a `light_rigs.toml` preset entry).

### 5.3 Animation — reuse timeline and export

- **Morph animation**: existing timeline keyframes on continuous params
- **Motion animation**: the preview shaders have **no** displacement/noise pass (only a box blur), so "Wobble" is expressed in the **`.es` rule transforms** as a time-dependent term — e.g. `rz (sin(time * 30) * 4)` — where `time`/`frame`/`fps` are bound per frame by the timeline (`core/lang/v2/front.py` `timeline_names`; static builds bind `time = 0`). Each frame re-evaluates the expressions and rebuilds — no new shader work, no builder change
- **Video export**: already supported (`structura animate --video` → `render/video.py`); Medusarium creatures render as MP4/WebM/GIF

### 5.4 Export — reuse mesh pipeline

Creature meshes export through the same `export/mesh/*` pipeline:
- OBJ/STL/GLTF with UVs, normals, and tags preserved
- USD exports with **PointInstancers** for instanced tentacles (existing `export/scene/usd.py` machinery — there is no `mda_instance` instancing path)
- Blender Geometry Nodes script (existing `export/scene/blender.py` + `blender_script.py.j2`): rules become node parameters; v2 `#param` sliders map to parameter inputs

---

## 6. Acceptance criteria

### 6.1 Minimum viable Medusarium (M1)

- [ ] `medusa.es` script loads and builds a valid SceneIR (no errors in builder or preview engine)
- [ ] Parameters panel shows all creature parameters with live updates on slider change
- [ ] Viewport displays wireframe and solid modes, switching via Render Settings preset
- [ ] Hatching pass produces the distinctive striped-illumination look (diffuse-controlled stripe density)
- [ ] Five-layer composition composite runs correctly (background → corners → hatch → highlights → borders)
- [ ] `structura export medusa.es -o medusa.obj` produces a watertight mesh with proper normals

### 6.2 Full creature editor (M2)

- [ ] Species morphing: save two configurations, animate between them on timeline
- [ ] Hair count and tentacle count control via integer sliders (snap to nearest int)
- [ ] Per-creature randomize: one click generates a new creature within artist-selected ranges
- [ ] Camera presets for species documentation (front, side, 3/4 view) with bookmarks
- [ ] Render report includes per-species statistics (primitive counts, triangle count, render time)

### 6.3 Polish & production (M3)

- [ ] "Medusa" preset in the Render Settings dropdown (integrator, lighting rig, camera, film compositing all pre-loaded)
- [ ] New panel: **Creature Explorer** (searchable gallery of saved creatures, with thumbnails from preview renders)
- [ ] Keyboard shortcut for morph animation start/stop/pause
- [ ] Documentation in `docs/user-guide/creatures.md`

### 6.4 Creature expansion — the wider fauna (M4)

Beyond the medusa, Haeckel's *Kunstformen der Natur* (the visual source for Cindermedusae) is famous for an entire gallery of marine invertebrates. M4 extends Medusarium to nine species in total: the three requested (radiolaria, hydra, shells) plus six further species drawn from the plates most associated with the book.

**DRY principle:** every new species reuses the M1–M3 machinery end-to-end (builder → SceneIR → preview → render → timeline → export). A species is a **parameter set + shared rule templates**, never a new pipeline (§3.1: these are v2 EisenScript patterns, not new geometry code). Most species are expressible with the existing M1 templates (`head`, `tentacle`, `hair`) plus four new templates introduced once and shared:

| New rule template | Used by |
|---|---|
| `spine_lattice` (radial/pleated lattice of tapered beams) | radiolaria, sea urchin, sand dollar |
| `spiral_whorl` (logarithmic-spiral tube with internal septa) | shells (gastropod/nautilus) |
| `zooid_chain` (repeated unit along a curved axis) | siphonophore, hydra |
| `striae_valve` (circular disk with radial pore lines) | diatoms |

| # | Species | Morphology | Key parameters (ParamSpec) | Templates |
|---|---|---|---|---|
| 1 | **Radiolaria** | Siliceous test: central sphere + radial symmetry of spines, interconnecting lattice, ornate apertures | `symmetry_order` (4–16), `spine_length`, `spine_taper`, `lattice_density`, `aperture_count` | `head` + `spine_lattice` |
| 2 | **Hydra** | Polyp: cylindrical body column, mouth disc, 1–2 rings of radial tentacles | `body_length`, `tentacle_ring_count`, `tentacle_length`, `stichocyte_density` (bump frequency) | `head` (flattened) + `zooid_chain` (tentacle ring) |
| 3 | **Shells** (gastropod + bivalve) | Logarithmic-spiral whorls with aperture; bivalve as mirrored twin valve | `whorl_count`, `growth_ratio` (b in r=a·e^(bθ)), `aperture_width`, `septum_spacing`, `rib_density` | `spiral_whorl` + `head` (bivalve valve) |
| 4 | **Siphonophore** | Colonial chain of repeating zooids (nectophores + doliols) along a curved nectosome axis | `zooid_count` (10–200), `zooid_type`, `chain_curvature`, `flagellum_length` | `zooid_chain` + `tentacle` (flagella) |
| 5 | **Ctenophore** (comb jelly) | Bell with 4–8 lobes and longitudinal rows of fused cilia (ctenes) | `lobe_count` (4–8), `ctene_row_length`, `iridescence` (hue-shift on fresnel angle) | `head` (lobed) + `hair` (ctene rows, dense & short) |
| 6 | **Sea urchin** | Spherical test with N long radial spines + tube feet; irregular base | `spine_count` (20–200), `spine_curvature`, `test_radius`, `tube_foot_density` | `head` + `spine_lattice` + `hair` (tube feet) |
| 7 | **Sand dollar** | Flattened echinoderm test with pentaradial "petal" pattern of spine bundles | `petal_count` (5, fixed by biology), `flattening`, `spine_bundle_density`, `margin_spines` | `head` (flattened) + `spine_lattice` |
| 8 | **Nautilus** | Chambered cephalopod shell: logarithmic spiral, curved septa walls, siphuncle canal | `growth_ratio`, `chamber_count`, `septum_curve`, `aperture` | `spiral_whorl` (septum option) |
| 9 | **Diatoms / protists** | Frustule (valve pair) with radial or parallel striae of pores; star, disc, and spiny forms | `striae_count` (12–96), `pore_shape`, `valve_thickness`, `spine_form` | `striae_valve` + `head` (spiny variants) |

**Implementation notes:**
- The four new rule templates (`spine_lattice`, `spiral_whorl`, `zooid_chain`, `striae_valve`) are **shared v2 script patterns** (§3.1) — e.g. `spine_lattice` is a radial `N * { ry (360/N) }` of tapered `cone`s, `spiral_whorl` a recursive rotate-translate-scale chain — reused across the species `.es` files; organic perturbation comes from the seeded random stream, not a new noise library (`core/geometry/noise.py` is only needed by the hatch pass).
- One example script per species in `resources/examples/creatures/` (`radiolaria.es`, `hydra.es`, `shell.es`, `siphonophore.es`, `ctenophore.es`, `urchin.es`, `sand_dollar.es`, `nautilus.es`, `diatom.es`), each pre-filled with an artist-tuned default range.
- The "Creature Explorer" panel (M3) is the species gallery: each entry is a species template + a saved parameter set; the existing thumbnail/preview-render machinery is reused.
- Morphing (M2) extends naturally: species-to-species morphs work where the parameter domains overlap (e.g. urchin → radiolaria both share `spine_lattice`); morphs between species with different primitive sets fall back to a crossfade (fade-out/fade-in) rather than geometric interpolation.
- The "Wobble" motion preset (M3) is species-aware: pendulum oscillation for medusa/hydra, gentle rocking for shells, slow spine sway for urchins.

**Acceptance criteria (M4):**

- [ ] All nine species build a valid SceneIR from their default `.es` (no builder or preview errors)
- [ ] Each species exposes ≥5 artist-tunable parameters with live preview updates
- [ ] Golden tests: 3 parameter variants per species produce watertight meshes on export (OBJ/STL/GLTF)
- [ ] At least one cross-species morph (urchin ↔ radiolaria) and one crossfade morph (medusa → nautilus) play correctly on the timeline
- [ ] Creature Explorer lists all nine species with thumbnails; loading one pre-fills the parameter panel

---

## 7. Naming suggestions

The user has already decided on **Medusarium / Medusoids**. Here are six additional naming options, ranked by alignment with the aesthetic:

| # | Name | Rationale |
|---|---|---|
| 1 | **Medusarium** | "Museum of medusa-like creatures"; academic, encyclopedic tone; matches Haeckel's illustration style |
| 2 | **Chthonic** | From Greek *chthonos* (underworld/earth); suggests deep, ancient organisms; sci-fi organic |
| 3 | **Xenofauna** | Latin *xenos* (foreign) + *fauna*; "alien fauna"; clear genre signal for sci-fi creature design |
| 4 | **Aethel** | Old English for "noble/elegant"; short, brandable, implies beauty and delicacy |
| 5 | **Bryozoan** | Scientific term for colonial jellyfish (Cnidaria); immediately signals the tentacle/jellyfish domain |
| 6 | **Sirenium** | From Greek *sirena* (sea nymph); mythic but not fantasy; implies aquatic, graceful organisms |

**Recommendation:** **Medusarium** — it's already decided by the user, it's clear what it is, and it matches Structura's academic/encyclopedic tone. The plan above assumes this name for all file paths.

---

## 8. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Creature geometry has manifold issues (non-manifold seams at head/tentacle joints) | Render artifacts, export fails | Use the existing `PyMeshLab` cleanup on export; build phase emits warning when edge count > 2 per vertex |
| Hatching pass is too slow for live preview | Viewport lags during parameter interaction | Run hatch as a single-shot post-pass after render completes (not in preview); provide "quick hatch" mode for the viewport |
| New creature params pollute existing Parameter panel | UI clutter, confusing for non-creature users | Gate behind a "Creature Mode" toggle or show only when `medusa.es` is open; add to a new tab group ("Organisms") |
| Hatch compositing on dark/semi-transparent regions creates color bleed | Visual artifacts on tentacles and thin spines | Clamp hatch pass to an opaque-silhouette mask before compositing with the base color; SSS is out of scope (not implemented) |

---

## 9. Next steps (immediate)

1. **Write the creature v2 scripts** — `resources/examples/creatures/medusa.es` first (bell + tentacles + oral arms + fringe, §3.1), verified with `structura build` and `structura render`; the shared rule templates (bell, tentacle chain, hair) are v2 patterns, not Python — a `core/geometry/creature/` module only if a shape proves inexpressible
2. **Register creature param specs** — the `#param` lines in `medusa.es` already drive the Parameter panel's dynamic form generation (slider per param); add the "Species" tab with morph presets
3. **Implement the hatching pass** (`render/kernels/hatch.py`) — reuses the existing lighting pipeline in `render/kernels/integrators.py`
4. **Build the five-layer film compositing** in `render/film.py` as an additional post-pass
5. **Write golden tests** for 5 creature variants (different parameter values) against expected output images

All steps follow DRY: no new render engine, no new scene model, no new UI framework. Only new rule templates, param specs, and a compositing pass.

---

*Prepared as an original, source-supported feature synthesis. The citations identify evidence used in the conversation; the source-location list keeps the Markdown independently useful after download.*