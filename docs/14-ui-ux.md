# 14 — UI / UX Design

## 1. Design language

- **Calm, content-first.** The script and the structure are the stars. Chrome is minimal and quiet, and takes
  its colours from the theme ([13](13-theming.md)).
- **Consistent metrics.**
  - 4 px base spacing unit (8/12/16 multiples); 6 px corner radius for panels and inputs.
  - 1 px borders using `ui.border`.
  - Shadows only on raised surfaces (popups, palettes).
- **Motion with purpose.** 150–200 ms ease-out for panel reveals, camera transitions and toasts. The *Reduce
  motion* preference disables them.
- **Fusion style + generated QSS** gives the same look on Windows, macOS and Linux. Native file dialogs and
  menus are kept for platform familiarity.
- **Never modal for long work.** Builds, renders and exports show progress in place (status bar, panel
  headers, the viewport ring). Structure Synth's blocking `QProgressDialog` is gone.

## 2. Main window

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ ◆ Structura   ▶ Build  ◉ Live   Seed [ 42 ] ⚄ +1   │  Workspace: Code · Explore · Render   ⌘K │ header bar
├────────┬──────────────────────────────────────┬──────────────────────────────────┬───────────┤
│ ▤ Files│  Default.es ●   Menger.es   +        │  Viewport │ Render                │ Inspector │
│ ☰ Outl.│ ┌──────────────────────────────────┐ │ ┌──────────────────────────────┐ │ Materials │
│ ◫ Exam.│ │ 1  set maxdepth 400              │ │ │                              │ │ Render    │
│ ⫶ Param│ │ 2  r0                            │ │ │        3D viewport           │ │ Environ.  │
│        │ │ 3  rule r0 {                     │ │ │   (click = jump to source)   │ │ Camera    │
│        │ │ 4    3 * { rz 120 } R1   ⟶ 3     │ │ │                        ⟳ 62% │ │           │
│        │ │ …                                │ │ └──────────────────────────────┘ │           │
├────────┴──────────────────────────────────────┴──────────────────────────────────┴───────────┤
│ Problems (2) │ Console │ Build Stats │ Render Queue │ Timeline │ Activity                   │ bottom dock
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ Ln 4, Col 18 · UTF-8 · EisenScript v1 · 102,400 objects (box 98%) · build 84 ms · CUDA: GTX 1660│ status bar
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Left activity rail:** Files (project explorer), Outline, Examples, Parameters. Each is a collapsible dock.

> **As built (M10):** the rail is a vertical icon tool bar at the window's left edge (`ui/dock_layout.py`). It
> holds every side panel — Files, Examples, Outline, Parameters, Camera, Inspector, Materials, Lights,
> Variations, Render Settings — and shows **one at a time** at full size; the active icon collapses the side
> bar. The "right sidebar" of property sheets was folded into the same rail: a second side bar would have
> squeezed the editor and viewport on laptop screens. Bottom panels are tabs along the top of the panel; a
> tabified dock hides its own title bar. View ▸ Panels lists all panels; Activity is hidden by default.
- **Centre:** the editor tab area and the view tab area (Viewport / Render), in a splitter. Either can be
  maximised (`Ctrl+Shift+M`).
- **Right sidebar:** contextual property sheets (Inspector, Materials, Render Settings, Environment & Lights,
  Camera).
- **Bottom dock:** Problems, Console, Build Stats, Render Queue, Timeline, Activity (jobs).
- All docks can be moved, floated and restored (`QMainWindow.saveState` per workspace).

### 2.1 Workspaces (`Ctrl+1…4`)

| Workspace | Layout emphasis |
|-----------|-----------------|
| **Code** | Editor wide, viewport medium, Problems visible |
| **Explore** | Viewport large, Parameters and Variation Explorer visible, editor narrow |
| **Render** | Render view large, Render Settings + Environment visible, Render Queue |
| **Present** | Full-screen viewport or render, with all chrome hidden (`F11`) |

> **As built (M10):** `ui/workspaces.py`. Code, Explore and Render are Ctrl+1 … Ctrl+3 and a menu in the
> header; each remembers its layout across sessions (first visit: the preset above). Present is Ctrl+4 (Esc
> returns); F11 stays plain full screen. View ▸ Workspace ▸ Reset Layout restores the default docks.

## 3. Panels

| Panel | Contents | Status |
|-------|----------|--------|
| Files | Project tree, open editors, file operations; `.structura`, `.es`, includes, templates | ✅ (folder view, new/rename/delete, follows the script) |
| Outline | Rules (ambiguous alternatives grouped, with weights and %), materials, params, v2 blocks; click to navigate; filter box | ✅ |
| Examples | Gallery grid with **thumbnails** (generated once by the `preview` integrator and cached), search, tags (Tutorials, Classic, Community); double-click opens a copy | ✅ gallery with cached thumbnails, group filter; opens copies |
| Parameters | `#define … (float/int)` and `#param` controls: sliders, spin boxes, colour buttons, toggles, enums; per-parameter keyframe toggle ([16](16-animation-scripting-cli.md)); reset-to-default | ✅ |
| Inspector | Picked-object info ([08](08-viewport.md) §6): kind, tag, material, generation, size, source link, "Show ancestry", "Select all from rule/tag/generation", "Hide/isolate" | ✅ info, go to source, select same call site/tag/generation/kind, isolate / show all, Show Ancestry (M11) |
| Materials | Tags found in the scene → material assignment; editor for principled parameters with a live preview swatch (`preview` render of a sphere+box); preset picker; "Write as v2 `material` block" | ✅ tags, presets, live swatch, writes v2 blocks |
| Render Settings | **Generated from registry ParamSpecs** ([02](02-architecture.md) §6.2): integrator, samples, noise threshold, size, filter, bounces, denoise, view transform, exposure, device | ✅ |
| Environment & Lights | Environment type (colour/gradient/HDRI/sun-sky) with HDRI browser and rotation; light list with add/remove; sun position widget (azimuth/elevation dial) | ✅ Lights panel (v2 light blocks); environment and sun in Render Settings |
| Camera | Numeric eye/target/up/fov/aperture/focus, projection type, **camera bookmarks** (saved views), "Copy camera to script" (v1 or v2 syntax), lock to script | ✅ numbers, standard views, saved views, Copy to Script, Lock to script (M11; saved in projects) |
| Problems | Diagnostics across open documents ([12](12-editor.md) §7) | ✅ |
| Console | Log with severity filters, search, copy; structured build/render statistics | ✅ |
| Build Stats | Counts by primitive kind; per-generation histogram; termination reasons (1.5 parity); timings per phase; memory; estimated vs actual object count | ✅ counts, termination reasons, generation histogram, time; per-phase timings (analysis, build, viewport; M11) |
| Render Queue | Queued/running/finished renders and exports, with progress, ETA, open/reveal buttons | ✅ (M11: exports are listed too, with progress and Cancel; they start at once on the io lane) |
| Timeline | Animation tracks ([16](16-animation-scripting-cli.md)) | ✅ |
| Activity | All Jobs with lane, state and duration (a debug aid, hidden by default) | ✅ |
| **Variation Explorer** | §5.3 | ✅ seeds and parameters, Expand Around This |


## 4. Commands, menus, shortcuts

**One `CommandRegistry`** (id, title, icon, default shortcut, enablement predicate, handler) feeds:

- the menu bar;
- the toolbars;
- the context menus;
- the **command palette** (`Ctrl+Shift+P` / `⌘K`);
- the keymap editor.

There are no hand-built duplicate `QAction`s (DRY).

### 4.1 Menu structure

> **As built:** the menus follow this table, with these differences. File has Export As… (Ctrl+E) and
> Open from Render…; Render has Add to Render Queue… (Ctrl+Shift+F9) and Save Render Report…; View has
> Panels, Workspace, Colour By, Overlays, Standard Views and Copy Camera to Script. M11 added the rest of the
> table: File ▸ Save as Legacy .es… (`core/lang/to_legacy.py`), Build ▸ Build Limits… and Show Ancestry,
> Build ▸ Run Python Script…, Render ▸ Render (Legacy Look), Render Region and Denoise, Edit ▸ Refactor…,
> and Help ▸ User Guide, Quick Start, Examples, What's New and System Report… ("Report Issue": the output of
> `structura doctor`, with Copy).

| Menu | Items (abridged) |
|------|------------------|
| File | New (`.es` / project), Open, Open Recent, Open from Render (PNG/EXR metadata), Save, Save As, Save as Legacy `.es`, Close Tab, Revert, Preferences, Quit |
| Edit | Undo/Redo, Cut/Copy/Paste, Find/Replace, Find in Files, Multi-cursor commands, Format Document, Toggle Comment |
| Insert | Legacy snippet groups ([12](12-editor.md) §8), pattern snippets, colour, current camera |
| View | Workspaces, panels, look preset, colour-by mode, camera presets & standard views, frame all/selection, grid/axes/bounds, full screen |
| Build | Build (`F5`), Live Build toggle, Cancel Build (`Esc` while building), Randomise Seed, Seed +1, Build Limits…, Show Ancestry |
| Render | Render in Viewport (preview), Render (`F9`), Render (Legacy Look), Render Region, Denoise, Save Render, Render Queue |
| Export | Mesh (OBJ/PLY/STL/3MF), glTF/GLB, USD, X3D, Blender Script, Template Export (`F6`), Image/Sequence/Video, Export Presets |
| Help | Quick Start, Language Reference (`F1`), Examples, What's New, Report Issue, About |

### 4.2 Default shortcuts (selection)

| Action | Shortcut | Note |
|--------|----------|------|
| Build | `F5` | Same as 1.5 |
| Template export | `F6` | Same as 1.5 |
| Render | `F9` / `Ctrl+R` | `F12` is reserved for *Go to definition* ([12](12-editor.md)) |
| Command palette | `Ctrl+Shift+P` / `⌘K` | |
| Quick open | `Ctrl+P` | Files, examples, symbols (`@`), lines (`:`) |
| Find | `Ctrl+F` | 1.5 used `Ctrl+F` for full screen; the *Legacy keymap* preset restores that |
| Full screen / Present | `F11` | |
| Randomise seed | `Ctrl+Shift+R` | |
| Seed ±1 | `Alt+→` / `Alt+←` | |
| Frame all | `F` (viewport focus) | |

Keymaps: *Structura* (default), *Legacy (Structure Synth 1.5)*, *VS Code-like*. All are user-editable.

## 5. Key workflows

### 5.1 First launch

A welcome page appears in the editor area: New, Open, Open Example, Recent, a theme picker showing four
thumbnails (Structura Dark/Light, Nord, Nord Light), and the detected compute device ("GPU: … ✓" or "CPU mode:
… cores"). The kernel warm-up runs in the background with a status-bar indicator.

> **As built (M10):** `ui/welcome.py` shows New, Open, Browse Examples, recent files, the four theme
> thumbnails and the render device (probed on the device lane); it fills the editor area whenever no script is
> open.

### 5.2 Opening a legacy file

1. Drag `Menger.es` in. It opens in v1 mode, and the status bar says "EisenScript v1 (Structure Synth 1.5
   compatible)".
2. If the script uses `set raytracer::*`, an info bar offers: "Render with Legacy look / Modern path tracer".
3. The script camera is applied on first build ([07](07-scene-model.md) §5).

### 5.3 Exploring: live coding + variations

- While typing, live rebuild shows results with a streaming progress ring. Number scrubbing and the parameter
  sliders give continuous updates.
- **Variation Explorer** (Explore workspace):
  - A 3×3 to 6×6 grid of *seed* or *parameter* variations.
  - Builds run sequentially on the build lane with a reduced object budget. Thumbnails come from the
    `preview` integrator, as GPU offscreen or CPU.
  - Click a cell to adopt its seed/params, star it to keep it, or "Expand around this" to jitter the
    parameters by ±x%.
- A snapshot strip (history) lets the user compare and restore earlier states. Each snapshot records the
  script hash, seed, params, camera and a thumbnail.

> **As built:** seed variations as described; the snapshot strip is the **History** panel (Build ▸ Take
> Snapshot, Ctrl+Alt+H: text, seed, parameters, camera and a viewport thumbnail; restore is one undo step).
> The Variation Explorer varies **seeds** or **parameters** (the `#define` sliders, ±25 % of each range around
> the current values, the first cell being the current state); right-click a cell ▸ Expand Around This halves
> the spread around it.

### 5.4 Final render

Render workspace → choose a preset (*Draft / Standard / Final / Print 4K*) → `F9` → watch the tiles → the
denoised result appears → *Save* (PNG/EXR, metadata embedded) or *Add to queue*.

> **As built:** presets Draft / Standard / Final / Print 4K in the Render tab; the render queue; progressive
> rendering instead of tiles ([09](09-renderer.md) §5.2). Save writes PNG/EXR with metadata; Report… writes a
> render report.

### 5.5 Export to Blender / USD

Export ▸ USD… opens a side sheet (not a modal dialog) with:

- instancing mode (PointInstancer / flattened);
- up axis (Y/Z);
- units;
- material mode;
- a live estimate of prims and file size.

The export runs as a Job, and a toast links to "Reveal in folder". Blender script export is analogous
([15](15-export.md)).

> **As built:** a Save As dialog (all formats, remembered folders) followed by the export sheet
> (`ui/dialogs/export_dialog.py`: destination, contents, presets, options). It is a short modal dialog, not a
> side sheet; no live size estimate yet. Exports run as jobs; a toast offers "Show in Folder".

## 6. Feedback & notifications

| Mechanism | Use |
|-----------|-----|
| Status bar segments | Cursor position, encoding, dialect, object count, build time, device, job spinner |
| Viewport progress ring | Build streaming, upload progress |
| Toasts (bottom-right, 4 s, stackable) | Completed exports, saved files, non-critical warnings |
| Banners (top of the relevant view) | Persistent conditions: CPU fallback, stale scene, legacy-mode hints |
| Panel badges | Problems count, Render Queue count |
| Modal dialogs | Only for destructive confirmations (unsaved changes) and fatal errors |

> **As built:** status bar segments, toasts (`ui/widgets/toast.py`, stackable, 4 s, Reduce motion), banners
> (`ui/banners.py`: legacy raytracer look, compute-preview fallback), the stale-scene badge in the viewport,
> and Problems count in the panel title. There is no progress ring in the viewport (the status bar shows
> build progress).

## 7. Preferences

The sections are generated from `SettingsService` ParamSpecs:

- General (startup, autosave, updates check: off by default);
- Appearance (theme, follow system, fonts, density, icon style, reduce motion);
- Editor (tabs/spaces, live rebuild delay, scrubbing sensitivity, inlay hints, format on save, keymap);
- Viewport (controls preset, orbit style, look, quality vs performance, line width);
- Rendering (device, CPU threads, memory guard %, denoiser, default preset);
- Paths (library/include paths, templates, HDRIs, output folder);
- Advanced (logging level, kernel cache, reset layout).

> **As built (M11):** `ui/dialogs/preferences.py`, one ParamForm per section in tabs (General, Appearance,
> Editor, Viewport, Rendering, Paths, Advanced), applied live by `ui/settings_actions.py`:
>
> - General: session restore, hot exit, the recovery-snapshot interval, language;
> - Appearance: theme, **follow the system's light/dark setting** (switches to the theme's pair, also when the
>   system changes), interface font (Inter or the system font) and size, **density** (comfortable/compact),
>   reduce motion;
> - Editor: code font (any installed monospace family), the view options (including Vim), live build;
> - Viewport: controls preset, engine;
> - Rendering: device, default render preset, CPU threads, **memory guard** (renders needing more than this
>   share of the free memory are refused with a message, `render/memory.py`);
> - Paths: default output folder, **library folders** for `#include`, the Blender executable;
> - Advanced: log level, **Reset Window Layout**, **Clear Caches** (compiled kernels, CUDA binaries,
>   thumbnails).
>
> Build limits (object cap, time limit, build memory guard) have their own dialog, Build ▸ Build Limits….

## 8. Accessibility & internationalisation

- Full keyboard operation. Every panel is reachable via `Ctrl+Shift+E/O/X/A/I` style shortcuts and the
  command palette. Focus rings are always visible (`ui.focus.ring`).
- Accessible names and descriptions are set on all custom widgets. The editor exposes the text to screen
  readers via Qt's accessibility bridge.
- High-contrast themes; colour-blind-safe defaults for colour-by modes (cividis/viridis ramps); diagnostic
  icons are shape-coded.
- UI scaling follows the OS, with an independent code font size.
- All user-visible strings use `tr()`. Qt Linguist `.ts` files are generated in CI. English ships first, and
  layouts are RTL-safe.

## 9. Module breakdown

```
structura/ui/
  app_window.py            # composition root (≤ 200 lines): creates docks, wires services
  commands/
    registry.py  builtin_file.py  builtin_edit.py  builtin_build.py  builtin_render.py  builtin_export.py  builtin_view.py
  menus.py  toolbar.py  statusbar.py  command_palette.py  quick_open.py  keymap_editor.py
  workspaces.py            # layouts + saveState per workspace
  welcome.py
  editor/ …                # see [12] §9
  viewport/ viewport_widget.py  hud.py  context_menu.py
  render_view/ image_view.py  aov_selector.py  compare.py  pixel_inspector.py  progress_overlay.py
  panels/ files.py  outline.py  examples.py  parameters.py  inspector.py  materials.py
          render_settings.py  environment.py  camera.py  problems.py  console.py  build_stats.py
          render_queue.py  timeline.py  activity.py  variations.py
  dialogs/ preferences.py  theme_editor.py  about.py  crash.py
  export_sheets/ mesh.py  gltf.py  usd.py  blender.py  template.py  image.py
  widgets/ param_form.py (ParamSpec → form)  color_button.py  slider_spin.py  sun_dial.py  toast.py  banner.py
```

`widgets/param_form.py` is the single generator of settings UIs. Render Settings, Preferences, export sheets
and material editors are all `ParamForm`s over ParamSpec lists (DRY).
