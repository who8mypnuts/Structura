# 22 — Implementation Notes

This document records where the implementation refines, corrects or departs from the plan in docs 00–21.
It also tracks each milestone's status. Each entry links to the section it amends. The chronological
detail is in [PROGRESS.md](PROGRESS.md).

## 1. Milestone status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0 Foundations & brand | ✅ done | Gates: ruff, mypy --strict, import-linter, size limits |
| M1 Language core v1 | ✅ done | 616/616 golden builds; bit-exact box records. The tolerant parser became a *recovering* parser for the editor (§2.8); builds keep the strict 1.5 parser |
| M2 SKL + precision engine | ✅ done | Five SKL targets, four compute backends, χ² and furnace tests, example renders |
| M3 App shell + preview + editor basics | ✅ done | GPU viewport verified on the owner's GTX 1660 (Wayland, after the desktop-GL fix of M9 part 3); compute preview everywhere else |
| M4 Export v1 | ✅ done | 252/252 template and 75/75 OBJ goldens byte-identical; 14 exporters with M8 |
| M5 Editor pro + themes | ✅ done | The docs/12 P0 and P1 checklists, including Find in Files, Quick Open and the colour picker (M10). P2 items are in the backlog (§4) |
| M6 Precision engine v2 | ✅ done | Every docs/09–10 feature except tiled bucket rendering (replaced by progressive + adaptive, §2.5) and pause/resume. Owner benchmark on the GTX 1660 still to be sent |
| M7 v2, animation, scripting | ✅ done | v2 blocks, expressions, `#param`, timeline, `#javascript` bridge, Python API, Variation Explorer, v2 primitives, `convert --to v2` |
| M8 Export v2 | ✅ done | 3MF, X3D/VRML, glTF instancing, USD policies, POV-Ray/Sunflow/Mitsuba writers, CSG, Blender GN (owner to verify in Blender), fog, photon caustics |
| M9 Hardening & 1.0 | 🟡 mostly done | Done: warm-up, i18n (English + German + pseudo), accessibility names, packaging scripts and CI, user guide, benchmark suite, UI-stall watchdog, GPU preview on NVIDIA/Wayland, cached CUDA binaries, time-paced passes. Open: the owner checks of §3 (installers, benchmarks, screen reader, native German review) |
| M10 Studio completion | ✅ done | The docs/14 window and panels, render reports, Save As flows, viewport colour modes, X-ray, isolation and overlays, navigation presets, render queue, pause/resume, History snapshots, export presets — see PROGRESS.md "M10" |

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

### 2.8 Editor ([12](12-editor.md))

- **Recovering parser instead of a CST parser.** When the strict 1.5 parser fails, the analysis re-parses
  with `RecoveringParser`, which notes each error and resumes at the next `rule` (rules never nest). The
  Problems panel then lists every broken rule, and the rules that parse keep feeding the outline, completion
  and go-to-definition. Builds still use the strict parser, so behaviour stays identical to 1.5. A full
  lossless CST (for refactorings) was not needed for any P0/P1 feature.
- **Colour picker:** non-modal `QColorDialog` with a live preview in the text; Cancel undoes; one undo step;
  the literal's style (hex length, case, names) is kept.

### 2.9 Window and panels ([14](14-ui-ux.md))

- **Activity rail + one side panel at a time**, instead of tabified side docks, whose tab labels became
  unreadable ("Exa…", "Ou…") at side-bar widths. Docks stay real `QDockWidget`s (movable, floatable, saved
  in the layout); a tabified bottom dock hides its own title bar because the tab names it.
- **Export sheet = Save As dialog + `ExportDialog`.** The native Save As dialog lists every format and
  decides it; the dialog that follows shows the full destination, the contents and the options. No live
  file-size estimate (backlog).
- **Materials and Lights panels edit the script** (v2 `material`/`light` blocks) rather than holding
  overrides outside it: the script stays the single source of truth, and renders and exports agree.
- **Colour-by modes recolour on the CPU** (io lane) and re-upload, instead of a shader uniform. It is one
  implementation for both viewports (the compute preview renders the recoloured scene).
- **Ground grid in the composite shader** (analytic plane, depth-tested against the G-buffer). Gizmo,
  bounds and HUD are a QPainter overlay shared by both viewports.
- **Render presets** set samples, image size (long edge, viewport aspect), noise threshold and denoising.
  The Render Settings panel's own noise threshold wins over the preset's.
- **Render queue** uses the device lane's FIFO: queued renders simply run after each other; an interactive
  F9 render waits behind them.

### 2.10 Render reports ([09](09-renderer.md) §8)

- Not in the original plan (owner request). `render/report/` collects a format-independent `Report`
  (sections of rows with raw values, display text and notes, plus thumbnail, histogram and palette).
  Writers: text, Markdown, HTML, JSON, CSV (Qt-free); PDF and ODT through `QTextDocument`
  (`services/report_documents.py`). The HTML sticks to tables and attributes that Qt's engine understands,
  and keeps browser-only CSS in a media query Qt ignores, so one HTML source serves the browser, the PDF and
  the ODT.
- Render jobs attach `RenderDetails` (resolved camera and settings, BVH figures, materials, lights,
  preparation time) to their updates, so reports describe exactly what was rendered.

## 3. Hardware checks for the owner

1. `pytest -m gpu` and the full parity suite. The `device` fixture includes CUDA, so every parity test also
   runs on the GTX 1660.
2. `python -m tools.bench.render_throughput --device cuda --size 1920x1080` (spike S2: ≥ 5 spp/s at
   1080p).
3. ✅ **Done (owner):** the GPU viewport runs on the GTX 1660 under Wayland after the desktop-OpenGL fix
   (M9 part 3), and GPU rendering works.
4. ✅ **Done (owner):** `structura doctor` on Wayland. The first report showed "Failed to create context:
   3009" / "OpenGL ES only" because Qt's EGL code picks an OpenGL ES config on NVIDIA unless desktop OpenGL
   is requested; the probe now requests it, with an automatic XWayland retry as a fallback.
5. `python -m tools.bench.suite` (all budgets of docs/18 §8; writes `bench-results.json`). Send the JSON file.
6. Run the UI tests with the reference budget: `STRUCTURA_STALL_MS=50 pytest tests/ui`.
7. Build the installers on each OS with `packaging/build.py` and the platform wrapper (`packaging/README.md`).
   None of them could run in the sandbox. Put the OIDN 2.x libraries in `src/structura/resources/oidn/`
   first, so the installers denoise with Open Image Denoise.
8. Blender 4.2 LTS: run an exported `.py` in both geometry modes (`baked`, `instanced`). The Geometry Nodes
   path (spike S5) is written against the 4.2 API but has not been executed.
9. Screen-reader pass (NVDA, VoiceOver) and a review of the German translation by a native speaker.
10. (M10) Look at the activity rail, workspaces and the Examples gallery at your screen size; save a render
    report as PDF and HTML and check them in your viewers; export with the Sunflow-Colored template to see the
    'runAfter' prompt.

## 4. Backlog — planned but not built

These items are in the plan documents but not in the program. None blocks 1.0 functionality; each has a
workaround.

| Item | Plan | Notes / workaround |
|------|------|--------------------|
| Tiled bucket renderer with bucket order | [09](09-renderer.md) §5.2 | Progressive rendering with adaptive sampling covers the same ground |
| Adaptive viewport quality (quarter-res SSAO while moving) | [08](08-viewport.md) §5 | Accumulation AA converges when the camera stops |
| "Show ancestry" trace rebuild; selection outlines in the compute preview | [08](08-viewport.md) §6 | Inspector selections tint alike objects (GPU viewport); Isolate Selection |
| Console severity icons; Outline listing of materials and parameters | [14](14-ui-ux.md) §3 | Console severity filter and search; the Materials and Parameters panels |
| Live file-size estimate in the export sheet | [14](14-ui-ux.md) §5.5 | The sheet shows the object counts |
| Template export sheet extras: template editor tab, output preview, "autosave script" | [15](15-export.md) §5.2 | Template export and its 'runAfter' command work |
| Vim keybindings; extract/inline-rule refactorings; hover thumbnails of rules | [12](12-editor.md) §2 (P2) | P2 by plan (post-1.0) |
| Preferences: autosave interval, memory guard, kernel-cache reset, sectioned layout | [14](14-ui-ux.md) §7 | CPU threads and the default folder are in Preferences; `structura warmup` rebuilds kernels |
| Windows/macOS signed installers, PyPI release | [19](19-roadmap.md) M9 | Scripts exist (packaging/); the owner builds and signs them |
