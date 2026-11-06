# 01 — Legacy Analysis

This document records what the three source bases contain, what is good and bad about each, and how each
concept maps to Structura. It is the evidence base for the decisions in later documents.

---

## 1. Structure Synth (canonical: `structuresynth-code-r312-trunk`)

### 1.1 Inventory (≈14,100 lines C++, Qt 4, QtScript, fixed-function OpenGL)

| Module | Files | Responsibility | Structura successor |
|--------|-------|----------------|---------------------|
| `StructureSynth/Parser` | `Preprocessor`, `Tokenizer`, `EisenParser` | `#define` substitution, GUI params, `random[a,b]`; whitespace tokenizer; recursive-descent parser | `structura.core.lang.*` ([06](06-language-engine.md)) |
| `StructureSynth/Model` | `RuleSet`, `Rule`, `CustomRule`, `AmbiguousRule`, `PrimitiveRule`, `TriangleRule`, `Action`, `Transformation`, `TransformationLoop`, `State`, `Builder`, `ColorPool`, `RandomStreams`, `ExecutionStack`, `RuleRef` | Rule graph, state propagation, breadth/depth-first expansion | `structura.core.lang.compile` + `structura.core.build` (Numba kernel) |
| `StructureSynth/Model/Rendering` | `Renderer` (abstract), `OpenGLRenderer`, `TemplateRenderer`, `ObjRenderer` | Visitor that receives primitives | Replaced by **SceneIR** ([07](07-scene-model.md)). Consumers read arrays; there is no visitor. |
| `StructureSynth/GUI` | `MainWindow` (1,791 lines), `TemplateExportDialog` (1,149), `VariableEditor` | Everything UI | `structura.ui.*` (many small modules) |
| `StructureSynth/JavaScriptSupport` | `JavaScriptParser`, `JavaScriptBuilder`, `Debug` | QtScript animation driver | `structura.scripting.legacy_js` (QJSEngine) |
| `SyntopiaCore/GLEngine` | `EngineWidget`, `Object3D`, `Box`, `Sphere`, `Grid`, `Line`, `Dot`, `Mesh`, `Triangle`, `RaytraceTriangle` | Immediate-mode GL preview | `structura.viewport` (WebGPU) |
| `SyntopiaCore/GLEngine/Raytracer` | `RayTracer`, `RenderThread`, `VoxelStepper`, `Sampler`, `ProgressiveOutput`, `AtomicCounter` | Multithreaded Phong+AO raytracer over a uniform voxel grid | `structura.render`, `classic` integrator ([10](10-renderer-shading.md) §2.1) |
| `SyntopiaCore/Math` | `Vector3`, `Matrix4`, `Random` (+ `MersenneTwister.h`) | Math and RNG | `structura.core.math`, `structura.core.rng` |
| `SyntopiaCore/Misc` | `ColorUtils`, `MiniParser`, `Persistence`, `Version` | Helpers | `structura.core.color`, value parsers |
| `Misc/*.rendertemplate` | 12 XML templates (Sunflow ×6, POV-Ray ×2, RenderMan, appleseed, Blender) | Text export | `structura.export.templates` (legacy engine kept) |
| `Examples/` | 29 scripts + 10 tutorials | — | Shipped, and part of the golden corpus |

### 1.2 Processing pipeline (as implemented)

```mermaid
flowchart LR
  A["Editor text"] --> B["Preprocessor<br/>define substring replace<br/>GUI params, random(a,b)"]
  B --> C["VariableEditor<br/>slider values substituted"]
  C --> D["Tokenizer<br/>split on whitespace / braces"]
  D --> E["EisenParser<br/>RuleSet"]
  E --> F["resolveNames<br/>class tags, triangle specs"]
  F --> G["Builder<br/>BFS or DFS on GUI thread"]
  G --> H["Renderer visitor<br/>OpenGL / Template / OBJ"]
```

### 1.3 Semantics that Structura must reproduce exactly (compat mode)

These were verified by reading the source. [05](05-eisenscript-language.md) formalises them.

1. **Transform composition is post-multiplication.** `child.matrix = parent.matrix * T`, so transforms are
   local.
2. **Rotations and scales pivot on the unit-cube centre.**
   `RX(a) = T(0,.5,.5)·R_x(a)·T(0,-.5,-.5)`; the same pattern applies for `ry`, `rz`, `s`, and `matrix`, each
   around (.5,.5,.5) or the matching axis centre.
3. **Loop counters start at 1.** `3 * { x 1 } R` places R at x = 1, 2, 3 (not 0, 1, 2). Nested loops
   (`a * {..} b * {..} R`) iterate as an odometer with the first loop fastest.
4. **"Previous state".** Any action with a transformation list records the parent's matrix, HSV and alpha.
   The `mesh` primitive uses this to sweep a quad tube from parent to child.
5. **Default state.** Identity matrix, HSV = (0, 1, 1) (**red**), alpha = 1. The OpenGL renderer sets the
   default background to **black**.
6. **Colour arithmetic is HSV.** `hue` adds degrees (wrapping), `sat` and `brightness` multiply (clamped to
   [0,1]), `alpha` multiplies. `color X` is absolute and goes through `QColor`, so saturation and value are
   **quantised to 8 bits** and achromatic colours report hue = −1. `color random` draws from the colour pool.
   `blend C s` mixes in HSV space: `(hsv + s·hsvC)/(1+s)`.
7. **Ambiguous rules.** Rules sharing a name form a weighted choice: `r = total·U[0,1]`, and the first rule
   with `r ≤ cumulative` is chosen.
8. **Depth limits.** Each state carries a per-rule remaining-depth map. `maxdepth N > R2` retires the rule to
   R2 at depth 0 and resets the counter. The global `set maxdepth` is a **generation limit** in
   breadth-first mode. In depth-first mode it is pushed into every rule without its own limit.
9. **Termination (BFS).** The build stops when generation ≥ maxdepth (default 1000), objects ≥ maxobjects
   (default **100,000**), or pending states ≥ maxobjects.
10. **Size culling.** `minsize` / `maxsize` compare `|M·(1,1,1) − M·(0,0,0)|` before a rule is applied.
11. **Random streams.** There are two MT19937 streams, *geometry* and *colour*, both seeded with the same
    seed. `MTRand::rand()` = `randInt() / 4294967295.0`, a closed interval. `randInt(n)` uses bit-mask
    rejection. Seeding uses the standard `init_genrand`. **Verified:**
    `numpy.random.RandomState(seed)._bit_generator.random_raw()` yields the identical stream (see [06](06-language-engine.md) §9).
12. **`set seed initial`.** This gives a state a stored seed. At each rule application the stream is reseeded
    from it and a new stored seed is drawn. This makes subtrees deterministic.
13. **Primitive geometry.**
    - `box`: unit cube under M.
    - `sphere`: centre M·(.5,.5,.5), radius |M·(.5,.5,.5) − M·(.5,.5,0)|. It is always round.
    - `line`: M·(0,.5,.5) → M·(1,.5,.5).
    - `dot`: M·(.5,.5,.5).
    - `grid`: the 12 edges of the box.
    - `triangle[p1;p2;p3]`: the points in object space.
14. **Camera.** `modelview = T(translation)·S(scale)·R(rotation)·T(−pivot)`; projection is
    `gluPerspective(fovy, aspect, near=5, far=60)`. Defaults: translation (0,0,−20), scale 0.4, identity
    rotation, pivot 0, fovy 22°. `set rotation [9 values]` is **row-major** (values 1–3 are row 0) and stored
    column-major internally (`v[row+col*4]`).
15. **Preprocessor quirks.**
    - `#define` performs **raw substring replacement**, not whole-word. Keys are applied in
      **alphabetical order** (QMap), restarting after every hit, with a cap of 100 substitutions.
    - Lines defining a recursive key are skipped with a warning.
    - `random[a,b]` is replaced per occurrence from its own MT stream seeded with the build seed.
16. **Tokenizer.**
    - Case-insensitive; user strings are lower-cased.
    - A `#` at the start of a line comments out the whole line after preprocessing.
    - `[` … `]` forms a single token, which allows spaces inside.
    - `a/b` integer fractions are numbers.
    - `>` must be whitespace-separated.

### 1.4 Defects and gaps found (fixed in Structura; v1 mode keeps the behaviour but warns)

| # | Defect | Evidence | Structura behaviour |
|---|--------|----------|---------------------|
| D1 | `cylinder` is registered as a primitive but `PrimitiveRule::apply` has no branch, so **nothing is drawn** | `PrimitiveRule.cpp` | v1: still emits nothing, with a lint warning. v2: real cylinder. |
| D2 | The menu inserts `size 2`, but `size` is not a tokenizer operator, so it is a **parse error** | `MainWindow.cpp:88`, `Tokenizer.cpp` | Accept `size` as an alias of `s` in both modes (no valid v1 script used it) |
| D3 | `v` is a tokenizer operator but the parser rejects it ("Unknown transformation type") | `Tokenizer.cpp`, `EisenParser.cpp` | `v` becomes an alias of `brightness` |
| D4 | `#include` is documented in the EBNF comments but **not implemented** | `EisenParser.cpp` header, `Preprocessor.cpp` | Implemented in both modes (v1: a line-level include) |
| D5 | `#define` substring replacement corrupts identifiers (`#define s 2` breaks `rule`) | `Preprocessor.cpp` | v1: reproduced, with a lint warning naming the affected tokens. v2: whole-word. |
| D6 | Triangles ignore class tags (`triangle[...]::tag`) | `bugs.txt`, `RuleSet.cpp` | v1 keeps 1.5 behaviour (it is a resolution error, see [05](05-eisenscript-language.md) C14); supported in v2 |
| D7 | Self-referencing retirement cycles crash (per `bugs.txt`) | `bugs.txt` | Verified to terminate in practice ([05](05-eisenscript-language.md) C15); the chain is bounded as a safety net |
| D8 | Operator names cannot be rule names (`> c` fails) | `bugs.txt` | v2 only: context-sensitive lexing |
| D9 | The build runs on the GUI thread with `QProgressDialog` and `processEvents` | `Builder.cpp` | A background Job ([04](04-concurrency-model.md)) |
| D10 | Global static RNG streams | `RandomStreams.cpp` | RNG state is owned per build |
| D11 | Memory leaks acknowledged in comments (`Action` pointer duplication) | `Action.cpp` | N/A (managed memory, array-based IR) |
| D12 | The `mesh` template primitive passes 18 numbers as `{matrix}` ("this really isn't a matrix") | `TemplateRenderer.cpp` | New `{mesh.*}` placeholders; the old ones are kept for legacy templates |
| D13 | The highlighter has "several errors" (regex-based, no shared lexer) | `bugs.txt` | The highlighter shares the real lexer (DRY) |
| D14 | Sphere resolution in OBJ export is limited to 2–40 divisions and vertices are de-duplicated with an O(n²) `indexOf` | `ObjRenderer.cpp` | Vectorised tessellation with LOD presets |
| D15 | Depth-first mode + `minsize`/`maxsize` culling loops forever: `continue` skips `removeFirst()` | `Builder.cpp` `recurseDepthFirst` | The culled state is popped (documented deviation) |

### 1.5 Feature parity checklist (everything Structure Synth 1.5 can do)

Every item ships in Structura 1.0. The column shows where each is specified.

| Feature | Spec |
|---------|------|
| Multi-tab editor with syntax highlighting, context-menu snippet insertion | [12](12-editor.md) |
| Build (F5), auto-increment seed, seed spin box | [14](14-ui-ux.md) |
| `#define` GUI sliders (float/int) | [05](05-eisenscript-language.md) §2.2, [14](14-ui-ux.md) |
| OpenGL preview: rotate, pan, zoom, Z-rotate, fast-rotate, coordinate system, reset view, full-screen | [08](08-viewport.md) |
| "Show 3D object information" (depth probe) | [08](08-viewport.md) §6 (now: full provenance picking) |
| Copy camera settings to the script | [08](08-viewport.md) §7 |
| Internal raytracer (in window / final), all `set raytracer::*` options | [10](10-renderer-shading.md) §6 |
| Template export, with template preview/edit, autosave of script, run-after command | [15](15-export.md) §5 |
| OBJ export (group by tag or colour, sphere resolution) | [15](15-export.md) §3 |
| Save viewport as bitmap | [08](08-viewport.md) §10, [15](15-export.md) §6 |
| Examples menu auto-populated from a folder | [14](14-ui-ux.md) |
| Recent files, drag & drop of `.es` files | [14](14-ui-ux.md) |
| `#javascript` movie scripts (`Builder.*`, `Debug.*`) | [16](16-animation-scripting-cli.md) §3 |

---

## 2. Sunflow 0.07.3 (basis of Structura Render; MIT, so code may be ported with attribution)

### 2.1 Inventory (≈30,800 lines Java, MIT licence)

| Package | Key classes | Notes |
|---------|-------------|-------|
| `core` | `Scene`, `LightServer`, `ShadingState`, `Instance`, `Geometry`, `PrimitiveList`, `Ray`, `IntersectionState`, `ParameterList`, `Options` | Clean separation: the API builds a `Scene`, an `ImageSampler` drives it, the `LightServer` shades |
| `core/renderer` | `BucketRenderer`, `ProgressiveRenderer`, `MultipassRenderer`, `SimpleRenderer` | Adaptive AA with contrast threshold, QMC subpixel sampling, bucket orders |
| `core/accel` | `BoundingIntervalHierarchy`, `KDTree`, `UniformGrid`, `NullAccelerator` | Two-level: instances over geometry |
| `core/gi` | `PathTracingGIEngine`, `AmbientOcclusionGIEngine`, `InstantGI`, `IrradianceCacheGIEngine`, `FakeGIEngine` | Pluggable GI |
| `core/photonmap` | `CausticPhotonMap`, `GlobalPhotonMap`, `GridPhotonMap` | Caustics and GI photons |
| `core/shader` | diffuse, phong, shiny, glass, mirror, ward, anisotropic ward, uber, amb-occ, constant, wireframe, textured variants, view/debug shaders (normal, uv, id, prim-id, quick-gray, irradiance, photons, caustics) | `Shader.getRadiance(ShadingState)` |
| `core/light` | point, directional spot, sphere, triangle-mesh, image-based (importance-sampled), **SunSky** (Preetham) | `LightSource` with sample/photon emission |
| `core/camera` | pinhole, thin lens (polygonal bokeh, rotation), spherical, fisheye | `CameraLens` |
| `core/filter` | box, triangle, gaussian, mitchell, catmull-rom, blackman-harris, lanczos, sinc, cubic B-spline | Pixel reconstruction |
| `core/bucket` | hilbert, spiral, column, row, diagonal, random, inverted | Tile ordering |
| `core/primitive` | sphere, box, cylinder, torus, plane, triangle mesh, quad mesh, hair, particle surface, julia fractal, sphereflake, banchoff, cornell box, cube grid, background | |
| `core/modifiers` | bump map, normal map, perlin | |
| `math` | `QMC` (Halton + Faure scrambling, sigma tables), `Matrix4`, `MovingMatrix4` (motion blur), `BoundingBox`, `OrthoNormalBasis`, `PerlinScalar/Vector` | |
| `image` | colour spaces, spectral curves, blackbody, readers/writers (PNG, TGA, HDR, EXR, IGI) | |
| `SunflowAPI` + `core/parser` | Programmatic API and `.sc` scene format | |

### 2.2 What we adopt

| Sunflow concept | Structura adaptation |
|-----------------|----------------------|
| `SunflowAPI` + `ParameterList` (string-keyed, typed parameters) | The `RenderScene` builder API with typed dataclasses. Parameter names stay Sunflow-compatible where possible so `.sc` export is trivial. |
| `PluginRegistry` (named factories for shaders, lights, filters…) | `structura.render.registry`: one registry pattern reused for integrators, materials, lights, cameras, filters, bucket orders and exporters (DRY) |
| `ImageSampler` variants | **Progressive** (interactive; `ProgressiveRenderer`) and **Tiled-adaptive** (final; `BucketRenderer` with contrast-driven refinement + variance stop) |
| `GIEngine` plug-ins | **Integrators**: `classic`, `ao`, `path`, `preview`, and `photon-caustics` (later phase) |
| `Shader` + `ShadingState` | The material system uses a **principled BSDF core**. Sunflow shaders become presets or specialised lobes ([10](10-renderer-shading.md) §3) |
| Two-level acceleration (`Instance` → `Geometry`) | **TLAS over instances + analytic/BLAS geometry**. This suits Structure Synth's millions of transformed unit primitives. |
| `BoundingIntervalHierarchy` | Binned-SAH BVH (BIH's memory-light idea is kept as the compact node layout) |
| `QMC` Halton/Faure | Sobol + Owen-scrambling sampler (integer-exact on GPU and CPU), with Halton kept as a selectable sampler for reference comparisons |
| Filters and bucket orders (complete sets) | Ported 1:1, used for filter-importance sampling and tile scheduling |
| `SunSkyLight`, `ImageBasedLight` (importance sampled), `ThinLens` (polygonal bokeh) | Ported 1:1 in behaviour |
| `Display` interface (`imageBegin/Prepare/Update/End`) | The `Film` emits Qt signals (`tile_updated`, `pass_completed`) through the render Job |
| `.sc` format | Export only, so users can still render in original Sunflow |

### 2.3 What we do not adopt

- Java-specific threading (one thread per bucket with `synchronized` accumulation). We use GPU dispatch, or a
  Numba `prange` over tiles.
- The Janino runtime-compiled shaders. User shaders are out of scope for 1.0.
- Per-object shader instances for every primitive (templates generated one shader per box). Structura stores
  colour per instance and uses one material per tag.
- `IrradianceCacheGIEngine` and `InstantGI` on GPU. They do not map well to GPU and are
  replaced by path tracing + denoising. The irradiance cache may come back as a CPU-only "fast GI" option after 1.0.

---

## 3. POV-Ray 3.8 (ideas only — AGPL-3)

POV-Ray's source is AGPL-3. Structura is MIT ([ADR-0010](adr/0010-licensing.md)). **No POV-Ray
code is transliterated.** We take only algorithms and features, and reimplement them from the public
documentation and the literature.

| POV-Ray idea | Where it lives in POV-Ray | Structura decision | Phase |
|--------------|---------------------------|-------------------|-------|
| Recursive adaptive anti-aliasing with threshold + jitter (AA method 2) | `render/tracepixel.cpp` | **Adopt.** Merged with Sunflow's contrast refinement in the final sampler | R2 |
| Statistical confidence test for focal blur sampling (`variance`, `confidence`) | `tracepixel.cpp` (`chdtri`) | **Adopt** as the per-pixel adaptive stop criterion | R2 |
| Orthographic, spherical (equirect), fisheye, panoramic, cylindrical cameras | `tracepixel.cpp` | **Adopt** orthographic, spherical and fisheye (panoramic via spherical) | R1/R2 |
| CSG (union / intersection / difference / merge) | `shape/csg.cpp` | **Adopt** for export (mesh booleans via manifold3d) and for legacy `template::difference-begin` templates. Render-time CSG is post-1.0. | E2 |
| Finish model: fresnel, metallic, brilliance, conserve_energy, iridescence, emission | `render/trace.cpp`, `material/*` | **Adopt** fresnel, metallic and emission inside the principled BSDF; thin-film iridescence post-1.0 | R2 |
| Radiosity (irradiance cache with pretrace passes) | `lighting/radiosity.cpp` | **Defer.** A possible CPU "fast GI" after 1.0 | — |
| Photon mapping for caustics (spatial targeting) | `lighting/photons.cpp` | **Adopt later** (with Sunflow's `CausticPhotonMap` as reference) | R3 |
| Atmospheric fog, homogeneous media | `scene/atmosphere.cpp`, `material/media.cpp` | **Adopt** simple exponential/height fog; heterogeneous media post-1.0 | R3 |
| Subsurface scattering | `lighting/subsurface.cpp` | Post-1.0 | — |
| Isosurfaces / quaternion Julia fractals | `shape/isosurface.cpp`, `shape/fractal.cpp` | Post-1.0 "SDF primitives" (Sunflow also has `JuliaFractal`) | — |
| Superellipsoid, torus, cone, lathe, sphere sweep | `shape/*` | **Adopt** torus and cone as v2 primitives; superellipsoid post-1.0 | L2 |
| `assumed_gamma`, file gamma handling | `base/image` | **Adopt:** an explicit colour pipeline (sRGB authored colours → linear rendering → view transform) | R1 |
| Render block patterns and mosaic preview | `backend/render` | **Adopt:** bucket orders + a coarse-to-fine first pass | R1 |
| Frontend/backend split via message passing (POVMS/VFE) | `povms/`, `vfe/` | **Adopt conceptually:** services communicate only through Qt signals/Jobs | F |
| Animation clock (`clock`, `frame_number`) | parser | **Adopt** as timeline variables in v2 expressions and in the legacy JS bridge | A |
| `#include`, `#declare`, `#macro`, `#while` | parser | **Adopt** `#include` (both modes) and compile-time expressions (v2). Macros and loops are not adopted, because EisenScript rules already provide them. | L1/L2 |
| Light groups, area lights (jitter, adaptive, circular), spotlights with falloff | `lighting/lightsource.cpp` | **Adopt** area/sphere/spot lights (Sunflow has most of these) | R2 |

Phase codes refer to [19](19-roadmap.md).

---

## 4. Summary of the refactor strategy

1. **Keep the language; rewrite the engine.** The language front end is reimplemented against the exact
   semantics above, and a golden corpus proves compatibility.
2. **Replace the renderer visitor with data.** The builder emits one struct-of-arrays SceneIR. The viewport,
   both renderer backends, every exporter and the stats panel read the same arrays. This removes the
   visitor duplication of `OpenGLRenderer`, `TemplateRenderer` and `ObjRenderer`.
3. **Port Sunflow's architecture, not its code style.** Its plug-in boundaries become Structura's registries.
   Its algorithms become single-source kernels that run on GPU and CPU.
4. **Borrow POV-Ray's best ideas** (adaptive sampling, cameras, CSG, finishes, fog) without its code.
5. **Break up god classes.** No file may exceed the limits in [17](17-code-standards-and-layout.md). The
   1,791-line `MainWindow` becomes about 20 focused modules.
