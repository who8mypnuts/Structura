# Changelog

All notable changes. The format follows [Keep a Changelog](https://keepachangelog.com/); versions follow
semantic versioning. The detailed record, with every deviation from the plan, is [docs/PROGRESS.md](docs/PROGRESS.md).

## [Unreleased] — 0.1.0

The first complete implementation of the plan in [docs/](docs/README.md) (milestones M0–M8, M10 and M11; M9
waits on the owner's platform checks).

### Owner review: glass, lenses, looks, recovery and clean-up

- **Glass:** coloured glass whose colour deepens with thickness (`attenuation_color`, `attenuation_distance`,
  also in the photon map), thin-walled panes, frosted refraction (`transmission_roughness`), anisotropic
  highlights, cut-outs (`opacity`) in every integrator, and material `model`s (constant, wireframe, ao,
  shadow catcher and debug views); the viewport approximates glass and metals.
- **Camera and lens:** focal length on a chosen sensor, f-stops at the scene's scale (`scale`), focus auto /
  hyperfocal / distance, bokeh bias and anamorphic squeeze, shift and tilt, fisheye mappings; a simple and an
  advanced lens editor in the Camera panel, the plane of focus in the viewport, focus on selection, focus and
  f-stop timeline tracks, lens options for `structura render`, and lens rows in render reports. Projects
  keep the lens (project format 2; older projects are migrated).
- **Looks:** bloom (energy-preserving), vignette, white balance, saturation, contrast and `.cube` LUTs — the
  Render view's Look (Off, Subtle, Neon, Cinematic, Studio) applies live; `render { look … bloom … }` in
  scripts; `--look`, `--bloom`, `--vignette`, `--lut` on the command line.
- **Lighting rigs:** Studio softbox, Sunset, Overcast, White studio, Night neon, Top light and Rim light,
  written by the Lights panel and sized to the structure. The Lights panel edits a light's values in a form.
- **Turntables:** Render ▸ Turntable… (loop or eased move, height, dolly) and Camera Path from Saved Views…;
  `structura animate --turntable`.
- **Render progress:** what the render is doing before the first pass (device, BVH, kernels), progress in the
  status bar and window title, the animation's progress bar.
- **Crash recovery:** a recovery snapshot seconds after every edit (every tab's text, parameters, render
  overrides, camera, saved views and timeline), backups before every save (File ▸ Recover), an error banner
  instead of silent failures, a rotating log and faulthandler crash log.
- **Render reports:** lens, declared lights, kernel start-up and per-pass times, device, peak memory, the
  look; a reproduce command with `--camera-from`; Copy Report as Markdown; Preferences ▸ Keep every render.
- **Tabs and frames:** Save / Don't Save / Cancel when closing a modified tab, Close Others / to the Right,
  middle-click, a tab context menu; render frames (16:9, 1:1, 9:16 …, custom) with a guide in the viewport.
- **MeshLab:** PyMeshLab clean-up presets on mesh export (clean, print-ready, light, smooth, remesh), Export ▸
  Check Mesh…, MeshLab project (`.mlp`) export, Open in MeshLab, a Run-after-export command.
- **Language:** `cylinder` draws in v1 scripts too (1.5 drew nothing); v2 blocks are checked against the
  catalogue (W115 unknown key with a fix, E017 bad value, W117 out of range); W116 misplaced `#version 2`,
  E018 v2 primitive in a v1 script; `render { view exposure denoise }` and `environment { sun NAME }`;
  `rand(a, b)` in expressions (documented, now implemented); File ▸ New v2 Script; a **Structura v2** group of
  showcase examples in the gallery.
- **Fixed:** a symbol the tokenizer rejects (`85mm` in a v1 script) crashed the analysis instead of reporting
  E004; cone apexes had degenerate triangles; the documented v2 examples that did not compile (a loop followed
  by a transform list); Open dialogs ignored the remembered folders; `ProblemsPanel.count_changed` was never
  connected; tests aborted when a QCoreApplication already existed.
- **Clean-up:** the old report stack, the unused side bar and CPU viewport, and their tests are gone; shared
  helpers for colours, vectors and the default sky; missing fonts, logo bitmaps and golden data restored.
- The `preview` and `ao` integrators (the compute viewport, gallery tiles) show a v2 script's sky; gallery tiles
  use the script's camera and look; large images are re-tone-mapped off the GUI thread; animation frames from
  the window use the Render view's look; saved images record the look; `structura doctor` lists PyMeshLab and
  Open Image Denoise.
- Docs: regenerated screenshots and example renders (`tools/example_renders.py`).
- Python 3.14 is supported (CI runs 3.12 and 3.14); PyMeshLab is a required dependency.

### Plan completion (M11)

- Tall panels scroll instead of growing the window past the screen; the window stays on its screen.
- Preferences in sections: fonts, density, follow the system's light/dark setting, default render preset,
  render memory guard, log level, library folders, Blender path, Reset Window Layout, Clear Caches.
- Renderer: a tiled bucket sampler (six bucket orders, bucket marks in the Render view), a mosaic first
  image, the Halton sequence, per-lobe bounce limits, AO direct light, the sinc filter.
- Viewport: adaptive quality while moving; Show Ancestry; Lock camera to script.
- Editor: Vim keybindings; refactorings (extract / inline rule, `{…} R` ↔ `1 * {…} R`); rule previews on
  hover; an object-estimate hint after top-level calls.
- Language: `#include`; colour, switch and choice `#param` controls; E012 and E015 diagnostics.
- Build: Build Limits (object cap, time limit, memory guard); capped builds while dragging a slider; a cache
  of recent scenes for undo and timeline scrubbing.
- Export: the template sheet (description, autosaved script, template editor, output preview), a size
  estimate, Open in Blender, exports in the Render Queue; File ▸ Save as Legacy .es.
- Scripting: the JavaScript Debug, World and Vector3 globals, run in a separate process so scripts can never
  freeze the window; `st.open()` documents in the Python API, `structura run file.py` and Run Python Script.
- Help: the user guide, What's New and a System Report inside the app.
- Render output dialog: the image file and a report beside it (PDF, HTML, Markdown, plain text, JSON, CSV or
  ODT) for Save…, queued renders and **Final Render…** (Shift+F9, or F9 with a final preset), which asks before
  rendering and saves both when it finishes.
- Fixed: check boxes and radio buttons had no visible box in any theme (the application style sheet hid
  Fusion's indicators); menus show a check mark for toggled items.
- Removed: the German translation.

### Window and workflow (M10)

- An activity rail: one readable side panel at a time (Files, Examples, Outline, Parameters, Camera,
  Inspector, Materials, Lights, Variations, Render Settings); bottom panels with tabs on top.
- Workspaces (Code, Explore, Render, Present) that remember their layouts; Reset Layout.
- A welcome page; toasts with Show in Folder; banners; an Activity panel of background jobs.
- An Examples gallery with cached thumbnails; examples open as copies.
- Save As dialogs everywhere, starting in remembered folders (never the program's folder).
- File ▸ Export As… with every format, an export sheet (destination, contents, presets, options), export
  presets shared with `structura export --preset`, and template 'runAfter' commands (after confirmation).
- File ▸ Open from Render: reopen the script and settings stored in a PNG or EXR.

### Language

- EisenScript 1.5, compatible: the golden corpus (154 scripts × 4 seeds) builds bit-identical structures.
  Template and OBJ exports are byte-identical to Structure Synth 1.5.
- EisenScript v2 (`#version 2`):
  - material, light, environment, camera and render blocks;
  - `( expressions )` with `frame` / `time` / `fps`, and `#param` sliders;
  - `mat` inheritance;
  - cylinder, cone, torus, ellipsoid and tube;
  - whole-word defines.
- `structura convert --to v2`, and Edit ▸ Convert to EisenScript v2.
- `#javascript` movie scripts through QJSEngine (`structura run`, F7).

### Editor

- Semantic highlighting, completion, signature help, hover and inlay hints.
- Diagnostics with quick fixes, rename, format, peek and references.
- Folding, multiple cursors, minimap, sticky scroll, split view and number scrubbing.
- A colour picker on right-click (live preview, one undo step, the literal's style kept) and a context menu
  with the language commands.
- Every broken rule is reported at once (a recovering parser for the editor).
- Snippets with tab stops.
- Sessions with crash recovery.
- 40 themes with a theme editor, keymap presets and an editor for them.

### Rendering

- A GLSL preview with a CPU fallback, and an OpenGL probe that avoids invisible windows.
- Precision engine from one kernel source on CUDA, OpenCL, WGSL and Numba:
  - path, AO, classic and preview integrators with a principled BSDF;
  - sun, point, sphere, spot and rect lights, and emissive geometry;
  - HDRI and Preetham sun-sky environments;
  - perspective, orthographic, spherical and fisheye cameras, with bokeh;
  - eight pixel filters, adaptive sampling and AOVs;
  - denoising with OIDN or À-Trous;
  - ground and shadow catcher, fog, and photon-mapped caustics;
  - AgX, ACES and filmic view transforms.
- Render view: live exposure and view transform, channels, denoise, zoom and pan, pixel inspector, A/B
  compare, region re-render, presets (Draft, Standard, Final, Print 4K), and a render queue.
- Render reports (PDF, HTML, Markdown, text, JSON, CSV, ODT) with geometry, camera, settings, image
  statistics, visible objects, BVH and performance figures; `structura render --report`.
- Viewport: colour-by modes, a ground grid, a technical look, gizmo/bounds/HUD overlays, navigation presets
  (Structura, Structure Synth 1.5, Blender) with a fly mode, standard views, animated camera moves, the Camera
  panel with saved views and Copy Camera to Script, the Inspector, CPU picking in the compute preview and
  Alt+click focus.
- The GPU viewport works on NVIDIA under Wayland (desktop OpenGL requested explicitly; XWayland fallback); the
  no-OpenGL fallback draws on the GPU with CUDA/OpenCL/wgpu. CUDA kernels are cached as machine code, and
  render passes are paced by GPU time.

### Animation

- A timeline with keyed parameters, seed and camera; scrubbing and playback.
- Render Animation to image sequences and MP4, WebM or GIF; `structura animate` reads projects.

### Export

- OBJ, PLY, STL (watertight), 3MF (instanced), glTF/GLB (optional GPU instancing), USD/USDZ (instanced,
  flattened or matrix policy), X3D, VRML97, and a Blender script (meshes or Geometry Nodes).
- POV-Ray 3.8, Sunflow and Mitsuba 3 scenes, and the 1.5 render templates.
- CSG markers evaluated with manifold3d.

### Platform

- A non-blocking GUI (job lanes, fair parallel sections, banded dispatch) with a UI-stall watchdog.
- Kernel warm-up, i18n infrastructure (English; a pseudo-locale for layout testing) and accessible names.
- Packaging scripts for Windows, macOS and Linux; CI workflows; a user guide.
- CLI: `theme list/check/import`, `devices`, `template`, and `structura FILE` to open the app.
