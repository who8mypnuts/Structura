# Structura — final work plan (approved decisions incorporated)

Status: **final plan, ready for implementation. No source files changed yet.**
Rules for every change: Python + PySide6, DRY (one concept → one implementation), Qt-free domain code
(`core`, `kernels`, `compute`, `render`, `preview`, `export`, `themes`), long work as Jobs on the right lane,
every new setting a `ParamSpec`, the size limits of `tools/check_sizes.py` (400 lines/module, 300/class,
50/function, nesting 4), the import-linter layers, and the CI gates (ruff, ruff format, mypy --strict,
lint-imports, check_sizes, gen_reference --check, update_translations --check, pytest).

## Decisions (from your answers)

| # | Question | Decision |
|---|----------|----------|
| 1 | Missing assets | **Restore them** (fonts, brand PNG/ICO/ICNS, golden data, screenshots, example renders) — Phase 0A |
| 2 | Lens scale | **1 world unit = 1 m** by default, with a "scene size" control |
| 3 | Materials panel | Every field **except the debug models** (`debug_*` stay script-only) |
| 4 | Crash handling | Non-modal banner + crash log + immediate recovery snapshot |
| 5 | MeshLab | **PyMeshLab becomes a required dependency** in `pyproject.toml` |
| 6 | Feature order | F1 post stack → F3 lighting rigs → F2 turntable |
| 7 | Python | **3.14 supported** (your local interpreter); 3.12 stays the floor |
| 8 | Cylinder | Added to the plan — investigation and fix in §Q9 |

## What changed since the first draft (new facts found)

- **The environment can run everything.** PyPI is reachable from the sandbox, and a local CPython 3.14.7
  exists (`/opt/uv-python`). I checked that **every runtime dependency has a CPython 3.14 wheel**: PySide6 6.12.0
  (abi3), numba 0.68, llvmlite 0.50, moderngl 5.13, wgpu 0.32, pyopencl 2026.1, pocl, cuda-python, usd-core 26.11,
  manifold3d 3.5.4, OpenEXR 3.5.2, imageio-ffmpeg, pygltflib, psutil, **pymeshlab 2025.7.post1**. Mesa (EGL/GL,
  llvmpipe), OpenCL and Vulkan loaders are installed. So implementation will run the real test suite offscreen,
  not just static checks.
- **pymeshlab caveats:** on Linux the 2025.7 wheels are `manylinux_2_35` (glibc ≥ 2.35: Ubuntu 22.04+, Debian 12+);
  Windows and macOS (x86_64 + arm64) have wheels for 3.12–3.14. Wheels are 55–107 MB. pymeshlab is GPL‑3.0:
  Structura's source stays MIT, but installers that bundle it ship a GPL‑covered combination — ADR‑0010 and
  THIRD_PARTY_NOTICES get updated to say so (no code consequence).
- **Cylinder root cause** (see Q9): the v2 cylinder is implemented in every consumer; what fails is the v1 path,
  where `cylinder` is deliberately invisible (Structure Synth 1.5 behaviour C10), plus several traps that make a
  script silently v1.
- **Asset sources:** GitHub/SourceForge are blocked here, but PyPI, npm and the Ubuntu archive are reachable,
  which is enough to restore everything (details in Phase 0A).

---

## Findings carried over from the examination

| # | Finding |
|---|---------|
| A | Two report implementations; `ui/report_actions.py`, `ui/reporting.py` import names that no longer exist → `mypy --strict` fails (CI red). Old stack: `render/report/data.py`, `text.py`, `templates/`. |
| B | Stale tests: `tests/ui/test_report_actions.py`, `test_save_paths.py`, `test_save_dialogs.py`, `test_sidebar.py`. |
| C | Dead modules: `ui/sidebar.py`, `ui/viewport/cpu_viewport.py`. |
| D | Material fields parsed and packed but never rendered: `transmission_roughness`, `attenuation_*`, `thin_walled`, `anisotropy*`; models `wireframe`, `ao`, `debug_*`. |
| E | `preview`/`ao` integrators and the AOV pass ignore alpha; the GL viewport ignores v2 materials. |
| F | Lens state split between `Camera` and `RenderSettings`; no focal length / f-stop / sensor. |
| G | No diagnostics for unknown keys/values in `light`/`camera`/`render`/`environment` blocks. |
| H | docs/05 lists `render { denoise view exposure }` and `environment { sun NAME }`, not implemented. |
| I | Binary assets missing from the archive (→ restore). |
| J | `__pycache__` (3.14) in the archive. |
| K | **New:** no bundled v2 example scripts at all (the gallery is 100 % v1), so v2 primitives, materials and lights have no discoverable demo. |
| L | **New:** `unit_cylinder(top_scale=0)` (cones) emits one degenerate triangle per segment (1/3 of the side triangles have zero area). Harmless for rendering, wasteful for exports and manifold checks. |

---

## Q1 — Glass / transparency (Phase 2)

Works today: `path` (rough dielectric BTDF, Fresnel, correct inside/outside), alpha pass-through in `path` and
`classic`, OIT in the GL viewport. Missing: Beer–Lambert absorption, transmission roughness, thin-walled,
anisotropy, the wireframe/ao/debug models, alpha in `preview`/`ao`/AOVs, materials in the viewport, glass fields
in the Materials panel.

Implementation:
1. **Absorption** — `render/kernels/path.py`: when a hit arrives from the inside (`h.front == 0`), multiply the
   throughput by `exp(−σ·t)`, `σ = −ln(attenuation_color) / attenuation_distance` of that surface's material
   (new SKL helper in a small `kernels/volume.py`). Exact for our closed convex primitives; no medium stack.
2. **Transmission roughness** — `bsdf.py`: `a_trans = max(ggx_alpha(transmission_roughness if > 0 else
   roughness), alpha_floor)` used for the whole glass lobe (refraction and its Fresnel reflection) in
   `principled_setup`, `transmission_value`, `bsdf_sample`.
3. **Thin-walled** — when `M_THIN`: straight-through transmission (micro-normal mirrored, no bending), outside
   Fresnel, no absorption.
4. **Alpha everywhere** — stochastic pass-through in `integrators.py` (`preview`, `ao`) and `aov.py`, reusing the
   `exclude` loop pattern and `PASS_LIMIT` from `path.py` (extracted into one `kernels/opacity.py` helper so the
   three integrators share it).
5. **Material models** — one `shade_model()` dispatch: `wireframe` (edge distance in object space / barycentric),
   `ao` (existing `ambient_occlusion()`), `debug_normal|id|uv|generation|gray`.
6. **Anisotropy** (after 1–5) — tangent = `normalize(cross(row1, row2))` of the stored inverse affine (the world
   image of the local x axis); anisotropic GGX D/G1/VNDF in `microfacet.py`.
7. **Materials panel** — add Model (principled, constant, wireframe, ao, shadow_catcher — **no debug models**),
   Opacity (state/number), Transmission roughness, Attenuation colour + distance, Thin-walled, Anisotropy +
   rotation. One table `core/scene/material.py: EDITABLE_FIELDS` drives the panel, `material_script.WRITTEN` and
   the reference (today they are two lists).
8. **Viewport approximation** (= QoL‑5).

Tests: absorbing-glass furnace (energy ≤ 1, thickness law), thin pane = straight through, anisotropic χ², backend
parity (OpenCL/WGSL/GLSL; CUDA on your GPU), an AO render of *City of Glass* that is visibly see-through.

## Q2 — EisenScript completeness (Phase 3)

v1 complete; v2 complete except D and H; lights and environments complete. Implementation:
1. **Validate every block from `catalog/v2_blocks.toml`** (generalising today's `MATERIAL_KEYS`): unknown key →
   new **W115** (warning, ignored) with a "did you mean …" quick fix (difflib) in `fixes.py`; bad value, bad
   choice, unknown light type → **E017**. The catalogue's `value` column is parsed once into validators, so
   completion, hover, reference and checks share one source.
2. **Implement the spec'd keys**: `render { view … exposure … denoise … }` (new `RenderSettings.exposure` and
   `denoise`; the Render tool bar shows the script's values like other overrides) and `environment { sun NAME }`.
3. **Lights panel property form** (catalogue-generated `BlockForm`, shared with the Materials panel's field rows)
   that rewrites blocks through `put_block`.
4. Docs: docs/22 §4 truthful; docs/10 preset path fixed; regenerate `docs/reference/language.md` and
   `resources/help/language.md` (`tools/gen_reference.py`).

## Q3 — Tabs (Phase 6)

All commands, panels and signals are wired (verified). Fix: Save / Don't Save / Cancel on close and quit; tab
context menu (Close, Close Others, Close to the Right, Close Saved, Save As…, Copy Path, Reveal in Folder) built
from registry actions; middle-click close; Open dialog starts in `SavePaths`; connect
`ProblemsPanel.count_changed` and delete the duplicate title code in `MainWindow.on_analysis`. Dead modules and
stale tests go in Phase 0B.

## Q4 — MeshLab with PyMeshLab as a required dependency (Phase 7)

`pyproject.toml`: add `"pymeshlab>=2025.7"` to `dependencies` (cp312–cp314 wheels on Windows, macOS and
Linux glibc ≥ 2.35). Imported lazily inside jobs only, so start-up time is unaffected; import-linter places it in
the Qt-free `export` layer; `mypy` already ignores missing stubs.

1. **One mesh bridge** — `export/mesh/meshlab.py` (Qt-free): `TriMesh ↔ pymeshlab.Mesh` (vertices, faces,
   per-vertex colour, owners kept in a vertex scalar attribute) and a small registry of named operations:
   `merge_close_vertices`, `remove_duplicates`, `reorient_coherently`, `close_holes`, `decimate` (quadric edge
   collapse to a face count or ratio), `remesh` (isotropic), `smooth` (Taubin), `recompute_normals`. Filter names
   are resolved against `pymeshlab.filter_list()` at first use, so a renamed filter fails with a clear message.
2. **Export sheet "Mesh clean-up"** for every mesh exporter (OBJ, PLY, STL, 3MF, glTF, X3D, VRML): a preset combo
   (None, Clean, Print-ready = clean + close holes + reorient, Light = decimate 50 %, Custom) plus the operation
   parameters as `ParamSpec`s. Applied in **one** place — the shared mesh export path after tessellation — so every
   format gets it; runs on the io lane with progress; shares `structura export --option meshlab=print-ready`.
3. **Mesh check** — `Export ▸ Check Mesh…` and a section in export reports: watertight, boundary edges,
   non-manifold edges/vertices, genus, volume, area, bounding box (`get_topological_measures`,
   `get_geometric_measures`). The STL watertight path (manifold3d) reports the same numbers for comparison.
4. **MeshLab project exporter (`.mlp`)** — one PLY layer per material/tag written with the existing PLY writer
   plus the project XML (or `MeshSet.save_project` when it round-trips colour correctly); registered in
   `export/api.EXPORTERS` so CLI, menu and Render Queue get it.
5. **Open in MeshLab** — generalise `ui/blender_app.py` into `ui/external_apps.py` (one finder/launcher; a data row
   per app: Blender, MeshLab; Preferences ▸ Paths ▸ MeshLab); toast + "Open when done" checkbox after mesh exports.
6. **"Run after export"** command field for every exporter, reusing the template `runAfter` code
   (`expand_command`, confirmation, Console output).
7. Licensing docs: ADR‑0010 and THIRD_PARTY_NOTICES (PyMeshLab GPL‑3.0, MeshLab/VCGlib); packaging README (glibc
   floor for AppImage/Flatpak builds).

Tests: TriMesh round trip keeps colours and counts; `close_holes` makes an open box watertight; decimate halves
faces within 5 %; `.mlp` parses with ElementTree and lists one layer per material; CLI option smoke test.

## Q5 — Lens: DoF, lens types, focal length (Phase 4, the largest)

Model, script, kernel, UI and reporting as in the first draft, with the scale decision fixed:

1. **`core/scene/lens.py`** — `Lens(projection, focal_length_mm, sensor_mm=(36, 24), fstop, aperture_radius,
   focus_distance, focus_mode=target|manual|hyperfocal, blades, blade_rotation_deg, bokeh_bias, anamorphic,
   shift, tilt, ortho_height, fisheye_fov_deg, fisheye_mapping=equidistant|equisolid|stereographic,
   units_per_metre=1.0)`; `Camera.lens`. Exact conversions `fov ↔ focal length` (sensor height) and
   `aperture_radius = focal_m / (2·N) · units_per_metre`; `dof_limits()` → near, far, hyperfocal (CoC = sensor
   diagonal / 1500). The seven duplicated `RenderSettings` fields move into `Lens`; `render/config.py` reads only
   `frame.camera.lens`; a one-release adapter accepts the old keys; project files migrate.
2. **Scene size** — "the structure is ≈ N m across" (from the bounds) sets `units_per_metre`; default 1 unit = 1 m.
3. **Script** — `camera {}` gains `focal_length`, `sensor 36x24|full-frame|aps-c|mft|1inch|phone`, `fstop`,
   `focus auto|hyperfocal|<d>`, `shift [x y]`, `tilt [x y]`, `bokeh_bias`, `anamorphic`, `mapping`,
   `lens "85mm portrait"`, `scale`; `fov`/`aperture` still valid; Copy Camera to Script writes the photographic
   form when a focal length is set; legacy save flattens to `set` lines.
4. **Kernel** (`render/kernels/camera.py`) — shift, tilt (focus plane rotated by the tilt angles, Scheimpflug),
   anamorphic and bias lens sampling, fisheye mappings; `CFG_SIZE` 80 → 96; parity on all backends.
5. **Camera panel** — *Simple*: lens preset (14/24/35/50/85/135/200 mm, Macro, Structure Synth 22°), focal-length
   slider ↔ FOV, *Depth of field* slider (f/22 → f/1.2), Focus: Auto / Click (Alt+click) / On selection /
   Hyperfocal, "Sharp from X to Y" readout. *Advanced* (collapsible): sensor, f-stop, radius, bokeh, shift/tilt,
   projection + mapping, scene size, Lock to script. **DoF guide overlay** in both viewports.
6. **Everywhere** — Render Settings loses its camera rows; report camera section (focal length, sensor, f-stop,
   DoF limits, hyperfocal, shift/tilt, preset); PNG/EXR metadata; projects; timeline `camera:focus`,
   `camera:fstop` tracks (focus pulls); CLI `--lens "50mm f/2.8" --focus --shift --projection`; API `lens=`.

Tests: round trips (fov↔mm, f-stop↔radius, script ↔ camera, project migration), DoF limits vs photographic tables,
kernel parity, panel two-way binding.

## Q6 — Crash recovery (Phase 5)

Edit debounce (5 s) plus the interval; snapshot always (saved tabs as paths) with a `running.lock` (pid) for crash
detection; `TabState` gains params, render overrides, camera, bookmarks and timeline through the project model's
encoders; `faulthandler` + rotating log in `<config>/logs`; `sys.excepthook` → log + immediate snapshot +
non-modal **Banner** "Structura hit an internal error — Details · Copy report · Continue" (job `ErrorInfo`s use
the same banner); File ▸ Recover… (declined snapshot, backups folder); backup copies on save (last 20) listed in
History. Tests: debounce, lock detection, full round trip, excepthook writes log + snapshot.

## Q7 — Render reports (Phase 8)

Exist and are thorough (PDF, HTML, MD, TXT, JSON, CSV, ODT, written beside the image). After removing the old
stack (Phase 0B): add lens rows, per-pass timings, kernel compile time, peak memory, GPU/driver/VRAM, each
light's values, post-stack rows, mesh-check rows for exports; preference "Write a report with every saved
render"; "Copy as Markdown"; reproduce command includes the lens/camera.

## Q8 — Progress (Phase 5)

Exists (tool-bar bar + ETA, queue, exports, CLI). Add: phase reporting from `render_job` ("Compiling kernels
(first run)…", "Packing…", "Building BVH…", "Tracing photons…") with an indeterminate bar until the first pass;
status-bar render segment and window-title suffix; animation frames drive the bar; a first-compile toast.

## Q9 — Cylinder "wired in but not functioning" (Phase 3)

**What I found.** The v2 cylinder (catalogue id 9) is implemented end to end: resolver, builder, `SceneIR` kind
`CYLINDER`, precision engine (`kernels/solids.py::hit_cylinder`, analytic), GL and compute previews (tessellated,
smooth normals), every modern exporter (`v2_shapes`, `affine_instances`). The geometry is sound — I checked the
unit cylinder's winding and volume numerically (0.7804 vs π/4 = 0.7854 at 32 segments). What makes it look
broken:

1. **In v1 scripts `cylinder` is deliberately invisible** — `krules.emit` counts it and returns without emitting
   (Structure Synth 1.5 behaviour C10). New scripts start as v1, so a typed `cylinder` draws nothing, with only
   a W105 warning and **no quick fix**.
2. **`#version 2` must be the first non-blank line** (`detect_dialect`). A comment above it silently makes the
   script v1; the misplaced line only produces the generic W120 "Could not understand preprocessor command".
3. Completion, hover and highlighting offer `cylinder`, `cone`, `torus`, `ellipsoid`, `tube` in v1 scripts as
   ordinary primitives; `cone`/`torus`/… then fail as E003 "Unable to resolve rule" instead of "needs #version 2"
   (W114 only looks at blocks, `#param` and `( … )`).
4. No snippet inserts a cylinder or any v2 primitive, and no bundled example uses one (finding K).
5. Cones produce degenerate triangles (finding L); legacy templates have no cylinder section.

**Fix:**
1. **Cylinders draw in v1 too.** Remove the `PRIM_CYLINDER` skip in `krules.emit` (v1's id 2 already maps to
   `PrimitiveKind.CYLINDER`, so every consumer handles it). Object counting is unchanged (already counted).
   1.5 byte-compatibility is kept where it is promised: the golden comparison ignores `CYLINDER` rows of v1
   scripts, and the legacy template and legacy-OBJ exporters skip v1 cylinders silently (1.5 emitted nothing).
   C10 in docs/05 §11 becomes "counted; Structura also draws them (1.5 did not)". W105 becomes an **info**:
   "Structure Synth 1.5 did not draw cylinders; legacy exports omit them". `convert --to v2` drops its cylinder
   note. *(If you prefer strict 1.5 behaviour, the alternative is to keep v1 invisible and only do items 2–5; I
   recommend drawing.)*
2. **Misplaced `#version 2`** → new diagnostic **W116** "#version must be the first line" with a quick fix that
   moves it up.
3. **v2-only primitives in v1 scripts** → W114 (with "Add #version 2" quick fix) instead of E003; completion marks
   them "(v2)" and accepting one in a v1 script offers to add `#version 2`.
4. **Snippets** for cylinder, cone[r], torus[r], ellipsoid, tube[r] (with tags), and File ▸ New ▸ **v2 Script**
   (a v2 starter that uses materials, a light and a cylinder).
5. **Cone apex**: one triangle per segment instead of a collapsed quad.
6. **Tests** — a v1 and a v2 cylinder through build → SceneIR, GL preview batch, compute preview pick, path render
   (AOV coverage matches the tessellated silhouette within 1 %), OBJ/PLY/STL (watertight)/3MF/glTF/USD/X3D exports,
   legacy template (omitted, byte-identical), quick fixes; golden suite still green.

---

## Three additional features (Phase 9, in this order)

**F1 — Post stack (bloom/glare, vignette, grading, LUT), live in the Render view.** Why: the biggest "pop" for
emissive structures and sun highlights, free at render time. What: `render/post.py` (numpy), `RenderSettings.post`
+ `render { bloom … }`, a Look popover with presets, recorded in saves, metadata and reports, CLI `--bloom`.
How: applied inside `to_display()` (one place for view, save, report); large images on the compute lane; tests for
bloom energy and LUT identity.

**F3 — Lighting rigs.** Why: beginners get a flat default sun. What: Lights panel ▸ Apply rig (Studio softbox,
Sunset, Overcast, White studio, Night neon, Top light, Rim light) writing `light`/`environment`/`render` blocks
sized to the bounds, replacing a previous rig, with preview thumbnails. How: `core/scene/light_rigs.toml` +
loader, `LightActions.apply_rig`, every rig builds and renders in a test.

**F2 — Turntable / camera-path wizard.** Why: the standard showcase, today seven hand-keyed tracks. What: Render ▸
Turntable… (revolutions, duration, elevation, easing, zoom, focus pull) writing editable Timeline keys and starting
Render Animation; "Path from saved views"; `structura animate --turntable`. How: `core/animation/paths.py`.

## Five QoL changes

1. **Tab handling** (Q3).
2. **Render size & aspect with a frame guide** — Viewport / 16:9 / 4:3 / 1:1 / 9:16 / Script / Custom; viewport
   letterbox overlay; honours `render { size }` (today the GUI ignores it).
3. **Render phase feedback** (Q8).
4. **v2 diagnostics** — W115/W116/W114/E017 with quick fixes (Q2, Q9).
5. **Materials approximated in the viewport** — transmission/opacity → OIT alpha, emission → unlit colour, metallic
   tint, base override; HUD note "materials approximated"; computed once per build from the `MaterialTable`.

---

## Execution phases

| Phase | Content | Done when |
|-------|---------|-----------|
| **−1 Environment** | `uv venv --python 3.14` (+ a 3.12 venv for the floor) with `-e ".[dev]"`; `QT_QPA_PLATFORM=offscreen`; record the baseline: which gates and tests fail before any change | baseline report in PROGRESS.md |
| **0A Assets** | **Fonts**: Inter 4.1 variable (`Inter-Variable.ttf`, `Inter-Variable-Italic.ttf`) and JetBrains Mono 2.x (`JetBrainsMono-{Regular,Italic,Bold,BoldItalic}.ttf`) from the official npm distributions (`inter-ui`, `typeface-jetbrains-mono`), WOFF2 → TTF with fontTools (lossless), name/version tables checked, SHA-256 and provenance in `resources/fonts/SOURCES.md`, and `tools/fetch_fonts.py` that prefers the upstream GitHub releases. **Brand**: `tools/brand/make_logo.py` (PNG icons 16–1024, mark, lockups @2x, `.ico`, `.icns`, review sheet); if the regenerated SVGs differ from the committed ones, the committed SVGs are kept and only rasterised. **Golden data**: rebuild the harness from the Structure Synth **1.5.0** source (Ubuntu `structure-synth_1.5.0.orig.tar.bz2`) and Qt **5.15.13** headers (Ubuntu noble `qtbase5-dev`, extracted in user space, exactly as the original harness did); `tools/golden/build_harness.py` gets a `--source` option; regenerate `tests/golden/data/**.xz` and verify **every run count and script SHA-1 against the committed `manifest.json`**. If any count differs (1.5.0 vs the r312 trunk the originals came from), I stop and report, and you supply the r312 checkout. **Screenshots**: `tools/screenshots.py` (window in themes, preview engine). **Example renders**: a new `tools/example_renders.py` writes `docs/renders/` reproducibly via the CLI. If you still have the original files, dropping them in wins over the regenerated ones. | `register_fonts()` returns Inter + JetBrains Mono; window icon loads; `pytest -m golden` collects 943 cases and passes; README images resolve |
| **0B Clean-up** | Delete the old report stack, dead modules, stale tests, `__pycache__`; DRY merges (colour helper, vector helpers, `resolve_view`, sky defaults); `count_changed`; Open-dialog folder; **pyproject**: classifiers 3.12–3.14, dependency floors raised to versions with cp314 wheels (verified with pip), `pymeshlab>=2025.7`; CI matrix adds 3.14; docs/22 §4 truthful | all gates green on 3.12 and 3.14 |
| **1 Cylinder & v2 UX** | Q9 items 1–6 | cylinder test matrix + golden green |
| **2 Glass & materials** | Q1 + QoL‑5 | furnace/χ²/parity; *City of Glass* AO see-through |
| **3 Language checks** | Q2 (W115, E017, spec keys, Lights form) | unit tests; reference regenerated |
| **4 Lens** | Q5 | parity, round-trip, migration, panel tests |
| **5 Progress & recovery** | Q6, Q8 | stalling-backend UI test; crash-lock and excepthook tests |
| **6 Tabs & size** | Q3, QoL‑1, QoL‑2 | UI tests |
| **7 MeshLab** | Q4 (pymeshlab bridge, clean-up, mesh check, `.mlp`, Open in MeshLab, run-after) | mesh tests; CLI option smoke test |
| **8 Reports** | Q7 | `tests/render/test_report.py` extended |
| **9 Features** | F1 → F3 → F2 | unit + one UI test each |
| **10 Docs & examples** | **v2 example folder** in the gallery (materials, glass, lights, cylinders/cones/tori, lens/DoF, rigs — finding K); user guide (rendering, camera, recovery, MeshLab, v2 quick start); "As built" notes in docs 05/09/10/14/15/22; ADR‑0010; CHANGELOG; PROGRESS.md | `gen_reference --check` green; examples build in a test |

Phase 1 moved ahead of glass because it is small, touches the builder that the golden suite guards, and unblocks
the v2 examples. Every phase ends with the full gate set on 3.14 and 3.12 and a PROGRESS.md entry; GPU-only checks
(CUDA parity, the tiled CUDA read-back) stay on your owner checklist because the sandbox has no NVIDIA GPU.

## Risks

- **Golden provenance** — regenerating from 1.5.0 instead of r312 may differ for a few scripts; the manifest
  counts catch it before anything is committed.
- **Lens refactor** touches ~25 files and project files; the adapter and migration keep old projects and scripts
  working for one release.
- **pymeshlab size and glibc floor** (≥ 2.35) — affects AppImage/Flatpak build images, not users of current distros.
- **Drawing v1 cylinders** changes what old scripts show (they gain visible cylinders); legacy exports stay
  byte-identical.
