# 22 — Implementation Notes

This document records where the implementation refines, corrects or departs from the plan in docs 00–21.
It also tracks each milestone's status. Each entry links to the section it amends. The chronological
detail is in [PROGRESS.md](PROGRESS.md).

## 1. Milestone status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0 Foundations & brand | ✅ done | Gates: ruff, mypy --strict, import-linter, size limits |
| M1 Language core v1 | ✅ done | 616/616 golden builds; bit-exact box records. The tolerant CST parser is not started: analysis uses the strict parser and reports the first error |
| M2 SKL + precision engine | ✅ done | Five SKL targets, four compute backends, χ² and furnace tests, example renders |
| M3 App shell + preview + editor basics | ✅ done | The GPU viewport is verified headless (EGL); the CPU preview is used on headless Qt platforms |
| M4 Export v1 | ✅ done | 252/252 template and 75/75 OBJ goldens byte-identical; 8 exporters (11 with M8's 3MF, X3D and VRML97) |
| M5 Editor pro + themes | ✅ done | The docs/12 checklist P0+P1: folding, multi-cursor, minimap, sticky scroll, split view, session/recovery, project files, linter + quick fixes, generated reference (F1), peek, breadcrumbs, provenance hover, snippets with tab stops, theme editor, keymaps, per-theme screenshot tests. Not done: Find in Files, Quick Open (Ctrl+P), Vim keybindings (P2) |
| M6 Precision engine v2 | ✅ done | Done: point/sphere/spot/rect lights, emissive-geometry NEE, HDRI + Preetham sun-sky with importance sampling, orthographic/spherical/fisheye cameras, polygonal bokeh, region render, 8 reconstruction filters, view transforms (AgX default), AOVs + multi-layer EXR, denoising (OIDN or À-Trous), adaptive sampling with a noise threshold and sample map, time limit, banded dispatch (cancellable within ~30 ms) with a fair parallel-Numba lock, ground plane and shadow catcher, the Render Settings panel, BVH speedups. Open: owner benchmark on the GTX 1660 |
| M7 v2, animation, scripting | ✅ done | Done: v2 blocks, expressions, `#param`, animation variables + `structura animate`, Python API, the `#javascript` bridge, the Variation Explorer. Done too: `mat` operator, v2 primitives (cylinder, cone, torus, ellipsoid, tube), whole-word v2 defines, `convert --to v2` (CLI + Edit menu), the timeline (keyed parameters, seed and camera; scrub, play, Render Animation; saved in projects; `animate` reads projects) |
| M8 Export v2 | ✅ done | Done: 3MF (instanced components or baked), X3D / VRML97 (DEF/USE with exact affine Transforms), glTF `EXT_mesh_gpu_instancing`, USD (PointInstancers, flattened mode, matrix shear policy), POV-Ray 3.8 / Sunflow / Mitsuba 3 scene writers (Jinja2), CSG markers evaluated with manifold3d, Blender Geometry Nodes instancing (owner to verify in Blender), fog, photon-mapped sun caustics |
| M9 Hardening & 1.0 | 🟡 started | Done: kernel warm-up (CLI + start-up job), i18n infrastructure (tr, catalogues, pseudo-locale, language preference), accessible names + scan test, packaging scripts (PyInstaller, AppImage, Flatpak, Inno Setup, DMG) and CI workflows, user guide, benchmark suite and first optimisations. Open: owner benchmarks and installer runs, real translations, screen-reader pass |

## 2. Refinements and deviations

### 2.1 Scene model ([07](07-scene-model.md) §2)

- **`SceneIR.xform` stores the exact builder state matrix** `[L | t]`, not Structure Synth's derived
  vectors `M·e − M·0`. The derived vectors lose low bits far from the origin. They are recomputed by
  `core.scene.ir.legacy_vectors` wherever 1.5 output is reproduced: golden comparison, legacy templates,
  legacy OBJ.
- `SceneIR.declarations` carries the v2 blocks (materials, lights, environment, camera, render).
  `SceneIR.subset(rows)` supports partial baking.

### 2.2 Compatibility details found with the goldens ([05](05-eisenscript-language.md) §11)

- C16: 1.5's `HSVtoRGB` evaluates `q` and `t` in double, then rounds once to float.
- C17: `QString::number` rounds exact decimal ties away from zero and prints −0 as `0`. The C library's
  printf does neither.
- C18: the OBJ exporter's grid segments use `vi + (j+1 % 4)`, so the fourth segment reaches into the next
  quad. Line faces also get normal indices that the de-duplication invents. Both are reproduced in the
  legacy OBJ layout only.

### 2.3 Concurrency ([04](04-concurrency-model.md))

- `JobRunner.submit` dispatches through a queued self-connection. A job can therefore never finish before
  the submitting slot has connected to its handle. Without this, fast jobs occasionally lost their
  results.
- Connect handle signals only to slots of QObjects on the GUI thread. Lambdas run on the worker thread.
- **Numba cache invalidation:** `core.jit` hashes every kernel source at import and drops cached kernels
  when any of them changes. Numba keys its cache by the defining file only, so inlined helpers from other
  modules would otherwise go stale.

### 2.4 Preview engine ([08](08-viewport.md))

- Picking reads one pixel of an id attachment synchronously after the frame, instead of PBO + fence. The
  read is one texel and it only happens on click.
- Weighted-blended OIT runs in **two passes** (accumulate, then revealage), because GL 3.3 has no
  per-attachment blend functions. A third "pick" pass writes see-through ids so they can be clicked.
- Boxes are split by the sign of their determinant, so back faces can be culled even for mirrored
  instances. Flat (singular) boxes are not culled.
- The QOpenGLWidget is created only when the GPU preview is wanted (`STRUCTURA_PREVIEW=auto|gpu|cpu|off`).
  Headless Qt platforms cannot show a child GL widget.

### 2.5 Precision engine ([09](09-renderer.md), [10](10-renderer-shading.md))

- The classic integrator turns 1.5's two recursive branches into a stochastic walk with the same
  expectation ([10](10-renderer-shading.md) §2.1 note).
- "Filtered caustics" raises GGX alpha to ≥ 0.3 after the first rough bounce.
- Point, sphere and spot lights use NEE without MIS. They are not geometry, so BSDF rays cannot hit them.
- SKL gained **buffer sets** (`@bufset`), a front-end rewrite that passes eight scene buffers as one
  argument ([11](11-compute-backends.md) §3.2).

### 2.6 Export ([15](15-export.md))

- Lines and grid edges are tessellated as square beams. Dots and spheres use UV spheres with LOD presets.
- USD per-instance colours use `primvars:displayColor` with *vertex* interpolation on PointInstancers,
  authored through `PrimvarsAPI`. PointInstancer is not a Gprim.
- The watertight STL union welds each instance's shell by quantised position first. The shared unit box
  has split normals, so it is not a manifold as stored.

### 2.7 Language v2 ([05](05-eisenscript-language.md) §9)

- v2 is implemented as **front passes** over the text (block extraction, `#param` → `#define` sliders, then
  `( expr )` after preprocessing). Line structure is preserved, so diagnostics and provenance map back
  unchanged.
- `#param` of type color, bool and enum becomes a plain define for now.

## 3. Hardware checks for the owner

1. `pytest -m gpu` and the full parity suite. The `device` fixture includes CUDA, so every parity test also
   runs on the GTX 1660.
2. `python -m tools.bench.render_throughput --device cuda --size 1920x1080` (spike S2: ≥ 5 spp/s at
   1080p).
3. Launch `structura-gui` on a desktop and check the GPU viewport. It has been verified through a real X
   server (Xvfb: GLX and EGL on llvmpipe) but not yet on Wayland or an NVIDIA driver.
4. Run `structura doctor` in the desktop session and keep its output. On the first report (Wayland), the
   driver rejected the 3.3 core context (`EGL_BAD_MATCH`). The probe now falls back to a compatibility or
   default context, or to the CPU preview. Which path your system takes is still to be confirmed.
5. `python -m tools.bench.suite` (all budgets of docs/18 §8; writes `bench-results.json`). Send the JSON file.
6. Run the UI tests with the reference budget: `STRUCTURA_STALL_MS=50 pytest tests/ui`.
7. Build the installers on each OS with `packaging/build.py` and the platform wrapper (`packaging/README.md`).
   None of them could run in the sandbox. Put the OIDN 2.x libraries in `src/structura/resources/oidn/`
   first, so the installers denoise with Open Image Denoise.
8. Blender 4.2 LTS: run an exported `.py` in both geometry modes (`baked`, `instanced`). The Geometry Nodes
   path (spike S5) is written against the 4.2 API but has not been executed.
9. Screen-reader pass (NVDA, VoiceOver) and a review of the German translation by a native speaker.
