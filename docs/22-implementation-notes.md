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
| M5 Editor pro + themes | ✅ done | The docs/12 P0 and P1 checklists, including Find in Files, Quick Open and the colour picker (M10); the P2 items (Vim, refactorings, hover previews) came in M11 |
| M6 Precision engine v2 | ✅ done | Every docs/09–10 feature; the tiled bucket sampler, mosaic pass, Halton sequence, per-lobe bounces, AO direct light and the sinc filter came in M11. Owner benchmark on the GTX 1660 still to be sent |
| M7 v2, animation, scripting | ✅ done | v2 blocks, expressions, `#param`, timeline, `#javascript` bridge, Python API, Variation Explorer, v2 primitives, `convert --to v2` |
| M8 Export v2 | ✅ done | 3MF, X3D/VRML, glTF instancing, USD policies, POV-Ray/Sunflow/Mitsuba writers, CSG, Blender GN (owner to verify in Blender), fog, photon caustics |
| M9 Hardening & 1.0 | 🟡 mostly done | Done: warm-up, i18n infrastructure (English UI; pseudo-locale for layout testing; German dropped at the owner's request), accessibility names, packaging scripts and CI, user guide, benchmark suite, UI-stall watchdog, GPU preview on NVIDIA/Wayland, cached CUDA binaries, time-paced passes. Open: the owner checks of §3 (installers, benchmarks, screen reader) |
| M10 Studio completion | ✅ done | The docs/14 window and panels, render reports, Save As flows, viewport colour modes, X-ray, isolation and overlays, navigation presets, render queue, pause/resume, History snapshots, export presets — see PROGRESS.md "M10" |
| M11 Plan completion | ✅ done | The M10 backlog and the remaining plan items: sectioned Preferences, Show Ancestry, template sheet extras, adaptive viewport quality, the tiled sampler and renderer extras, Vim/refactorings/hover previews, `#include`, typed `#param` controls, build limits and the scene cache, the JavaScript globals (in a separate process), the Python `Document` API, the remaining menu commands — see PROGRESS.md "M11" |
| M12 Owner review | ✅ done | Glass and materials, the photographic lens, looks (post stack), lighting rigs, turntables, render progress, crash recovery, richer reports, tab handling and render frames, MeshLab, clean-up — §2.11 and PROGRESS.md "Owner review" |

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
  (M11 fixed three places that still used lambdas: saving renders/reports, the autosaved template script
  and the legacy copy.)
- **Build limits** (M11) are checked between build slices: an object cap, a time limit and the memory
  guard (the builder's buffers against a share of the free memory). While a parameter slider is held,
  builds are capped at 250k objects; the full build follows on release. Finished builds are cached by
  (analysis digest, seed, limits).
- **Numba cache invalidation:** `core.jit` hashes every kernel source at import and drops cached kernels
  when any of them changes. Numba keys its cache by the defining file only, so inlined helpers from other
  modules would otherwise go stale.

### 2.4 Preview engine ([08](08-viewport.md))

- Picking reads one pixel of an id attachment synchronously after the frame, instead of PBO + fence. The
  read is one texel and it only happens on click.
- **Adaptive quality** (M11) drops SSAO on moving frames only when a GL timer query showed that full frames
  take more than 22 ms; the shadow map is cached across camera moves. Quarter-resolution SSAO and FXAA were
  not needed.
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
- **Tiled sampler** (M11): the render kernel takes a column offset too, so one bucket is one dispatch;
  `Bound.read_range` (every backend) reads back only the bucket's rows. Both samplers use the same global
  per-pixel sample indices, so they give the same image.
- **Sample numbers** are hashed per (pixel, sample, dimension), not Sobol; `sequence halton` (M11) switches
  the first dimensions to a rotated Halton sequence. Faure's permutations are not ported.

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
- `#param` of type color, bool and enum becomes a typed define (`#define NAME VALUE (color)`, `(bool)`,
  `(enum:a|b)`) that the v2 preprocessor turns into a parameter with a colour button, switch or choice list
  (M11). Its value travels as a float like the sliders' (0xRRGGBB, 1/0, the choice's index), so every
  parameter path (panel, projects, variations) stays one path.
- **`#include`** (M11) is expanded before the v2 front passes; `core/lang/includes.Expansion` maps spans from
  the expanded text back to the edited file (included lines map to their `#include` line).

### 2.8 Editor ([12](12-editor.md))

- **Refactorings without a CST** (M11): `core/lang/restructure.py` rewrites actions by the parser's spans,
  mapped back through the PositionMap, and only where the mapped text equals the parsed text (no `#define`
  substitution on the action). That was enough for extract, inline and the count toggle.
- **Vim** is an event filter installed in front of the editor's other key filters; insert mode passes
  every key through except Escape, so completion, snippets and multi-cursor keep working while typing.
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
  decides it; the dialog that follows shows the full destination, the contents, the options and (M11) a live
  size estimate: two small samples of the scene are exported for real on the io lane and extrapolated
  (`export/estimate.py`).
- **JavaScript runs in a separate process** (M11). `QJSEngine.evaluate` keeps Python's GIL while JavaScript
  runs, so even on a worker thread a long pure-JavaScript loop froze the GUI. The window now runs
  `structura run --ipc` in a QProcess and talks to it with JSON lines (`services/script_process.py`).
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

### 2.11 Owner review (glass, lenses, looks, recovery)

- **Cylinders draw in v1 scripts.** Structure Synth 1.5 parsed `cylinder` and drew nothing; Structura draws
  it everywhere (owner decision). The golden comparison skips CYLINDER rows, the template engine skips v1
  cylinders silently (1.5's templates never saw one), and `W105` became an info note. `E018` reports a v2-only
  primitive in a v1 script, `W116` a `#version 2` that is not on the first line.
- **Glass** follows the principled model with Beer–Lambert absorption (`kernels/volume.py`) applied on exit
  through a transmissive surface, in the path integrator and the photon pass alike; `thin_walled` skips the
  bending; cut-out opacity is honoured by every integrator and by the AOVs (`kernels/opacity.py`). Material
  `model`s are evaluated in `kernels/models.py`; debug models are script-only (not offered in the panel).
- **The lens** lives on the camera (`core/scene/lens.py`), not in the render settings: 1 world unit = 1 m by
  default, `scale` changes it; the kernel gained shift, tilt (a tilted focus plane via `focus_normal`),
  bokeh bias, anamorphic squeeze and fisheye mappings (cfg slots 76–83). Projects moved to format 2 (the
  lens in the camera; older projects are migrated). Legacy `raytracer::dof` still resolves against the view.
- **The post stack** (`render/post.py` settings, `render/post_image.py` operations, `render/lut.py`) runs where the image is displayed or saved
  (`render/output.Display`), never on the radiance: EXR stays linear, every change is live, and one
  `Display` value (exposure, view transform, post, asset folder) travels from the tool bar, the script or the
  command line to every writer. Bloom adds exactly intensity × the light above the threshold.
- **Lighting rigs** are data (`core/scene/light_rigs.toml`): offsets and sizes in bounding radii, and an
  *irradiance at the centre* from which the power follows, so a rig looks the same at any scale.
- **Recovery:** the session file doubles as the recovery snapshot; `CrashGuard` (a running lock with the
  PID) tells a crash from a clean exit. Snapshots follow edits after 5 s; unhandled exceptions in slots and
  threads reach an error banner (`ui/error_reporting.py`) and the rotating log (`app/diagnostics.py`).
- **Reports:** backends describe their device (`Backend.details()`); progress carries per-pass and kernel
  times; reports add lens, lights, memory and the look, and the reproduce command repeats `--camera-from`,
  the exposure and the look.
- **MeshLab:** PyMeshLab (GPL-3, ADR-0010 amendment 1) is imported lazily for clean-up presets and Check
  Mesh; the `.mlp` exporter writes one PLY layer per group.
- **Found and fixed:** `analyze()` raised on a token the v1 tokenizer rejects (now E004); `rand(a, b)` was
  documented but not implemented; the user guide's v2 example did not compile (a loop followed by a
  transform list — the documentation's v2 examples are now compiled by a test).

- **Round 2 (owner feedback):** the viewport menu and modifier keys (`ui/viewport/navigation.py`, `ui/
  viewport_menu.py`), live Preferences preview, the renderer's scene-version key (X-ray), overlay repaint on
  `frameSwapped`, the probe's hidden-window fallback and the honoured Viewport engine preference.

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
9. Screen-reader pass (NVDA, VoiceOver).
10. (M10) Look at the activity rail, workspaces and the Examples gallery at your screen size; save a render
    report as PDF and HTML and check them in your viewers; export with the Sunflow-Colored template to see the
    'runAfter' prompt.
11. (M11) Render with Image sampler = tiled on the GTX 1660 (the CUDA bucket read-back only runs there); try
    Vim mode and the refactorings (Ctrl+Alt+R); run a `#javascript` movie script from the window and cancel it.
12. (Owner review) On the GTX 1660: `pytest tests/parity -m gpu` (the new glass absorption, opacity, lens
    shift/tilt/bias/anamorphic and fisheye paths compile for CUDA in the sandbox — `tests/parity/
    test_cuda_compile.py` — but have only run on the CPU backend); render the *Structura v2* examples; try a
    turntable with video; apply each lighting rig to one of your scripts.
13. (Round 2) If the viewport still says OpenGL 3.3 is unavailable on the NVIDIA machine: send the banner's
    *Details* (or `structura doctor`), then try *Use OpenGL anyway*; with `WAYLAND_DISPLAY` set, also
    `QT_QPA_PLATFORM=xcb structura-gui`.
14. (Owner review) Decide the installers' PyMeshLab licensing (ADR-0010 amendment 1) before the first public
    installer; on Linux check the AppImage finds `libOpenGL.so.0`.

## 4. Backlog — planned but not built

Every feature of the plan documents is in the program (M11 closed the list that stood here after M10).
What remains is work only the owner can do, and a few deliberate omissions:

| Item | Plan | Notes |
|------|------|-------|
| Windows/macOS signed installers, PyPI release | [19](19-roadmap.md) M9 | Scripts exist (`packaging/`); the owner builds and signs them (§3) |
| Faure permutations for the Halton sequence | [09](09-renderer.md) §4 | The rotated Halton sequence is there for comparisons with Sunflow |
| W111 "build cap reached" as a diagnostic | [05](05-eisenscript-language.md) §10 | A build result, not an analysis result: the status bar, Build Stats and the build-limit message say it |
| Project sections for materials, lights and the environment | [07](07-scene-model.md) §8 | Kept when a project is read and written; the script's v2 blocks hold these (the Materials and Lights panels edit them) |
