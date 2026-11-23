# Knot Panel Plan — the proposed **“Knots”** dock panel in Structura

Date: 2026-11-21
Status: **planning only — no source files were changed for this document** (updated 2026-11-22: the knot surface
is a **dock panel**, not an editor tab, per owner clarification; updated 2026-11-23: Phase 0 implemented — see
§14)
Scope: the feature request “add a new dock panel called ‘Knots’ to Structura” (editor, picker gallery, live
preview, materials / styles / looks, save-as-structure) as it would be realised against the current codebase.

Owner context: `/home/stan/Work/python/Structura` (EisenScript/Structure Synth successor, PySide6,
preview GLSL + precision path tracer) and the reference knot material in
`/home/stan/Work/python/Structura/planning/knotplot` (KnotPlot by Robert G. Scharein / Hypnagogic Software).

---

## 1. The request, restated

1. A new dock panel in Structura called **“Knots”** (hosted in the main window’s dock area, *not* as a tab in the
   document/editor tab strip).
2. Inside it: an **editor** that lets users **edit their knots**.
3. A **picker gallery** with a **large list of established, pre-defined knots** that users can **pick from** and
   then **edit their algorithms** on top of.
4. A **previewer** “just like with the main structura window”, live as the knot is edited.
5. **Many materials, styles and looks** applicable to the knots; the result must be **easily rendered out just
   like the main program**.
6. **Save the knots we create, or use the pre-existing ones, as structures in the original structura script
   editor** — i.e. a saved knot must become a real, openable, editable *structure* in Structura’s own
   EisenScript editor and render through the ordinary pipeline.

This is a large project. The plan below is deliberately meticulous: it records what exists today, what must be
built, in which phase, and how each phase plugs into the architecture that is already in place.

---

## 2. What I found in the current Structura code (the “current code”)

Everything below is verified against the working tree at `71e3f96` (`src/`, `tests/`, `tools/`, `docs/`,
`src/structura/resources/`). A repo-wide search for the substring `knot` (case-insensitive) over
`src/`, `tests/`, `tools/`, `docs/` returns **no hits** — Structura today has **no knot concept at all**; the
word is used only in unrelated contexts (e.g. AI texture prompts, knot-tying metaphors). The knot feature must
therefore be built on a green field, but on top of a very solid existing spine.

### 2.1 The architectural facts the plan leans on

- **Layering (docs/02-architecture.md §1–2):** `core` (pure Python + numpy/numba) → `kernels` (SKL) →
  `render` (BVH, integrators, film) and `preview` (GLSL + Numba) → `export`. Qt only in `services` (QtCore
  signals) and `ui` (QtWidgets). Import-linter contracts are enforced in CI.
- **The scene is a struct-of-arrays `SceneIR`** (frozen dataclass; `kind`, `xform`, `rgba`, `tag`, `source`,
  `generation`, `aux`, `aux_data`, `tags`, `events`, `declarations`), one row per emitted primitive
  (`src/structura/core/scene/ir.py:20–126`). Row order = emission order; `xform` is the (N,3,4) `[L | t]`.
- **Kinds** are `PrimitiveKind` IntEnum values plus the builder-primitive-id mapping `LEGACY_KIND`
  (`src/structura/core/scene/ir.py:20–55`). Today: `BOX, SPHERE, ELLIPSOID, CYLINDER, CONE, TORUS, LINE, TUBE,
  DOT, GRID, MESH, TRIANGLE, TEMPLATE` (values 0–12).
- **The EisenScript v1 primitives** are catalogued in
  `src/structura/core/lang/catalog/primitives.toml` (names `box, sphere, cylinder, mesh, line, dot, grid,
  template` + `[[v2_primitive]]` rows: `cylinder id=9, cone id=10, torus id=11, ellipsoid id=12, tube id=13`).
- **Builder kernel** (`src/structura/core/build/krules.py`): `PRIM_*` constants (lines 53–57), `emit` (169–208),
  `has_param` (140–142), `_aux_row` (146–166) — parameterised kinds carry the bracket value in the aux row,
  meshes carry frames/colour, triangles carry corners.
- **Tessellation** (`src/structura/core/geometry/tessellate.py:84–91`, `v2_shapes.py`): kinds are iterated as
  `for kind in (K.BOX, K.SPHERE, K.DOT, K.LINE, K.GRID, *V2_KINDS)`; `_kind_mesh` dispatches per kind; `V2_KINDS
  = (K.CYLINDER, K.CONE, K.TORUS, K.ELLIPSOID, K.TUBE)`; `tube_ends` / `_tubes` for `K.TUBE`.
- **Preview**: `PreviewScene` batches (`boxes, spheres, dots, lines, grids, triangles`) in
  `src/structura/preview/instances.py:55–75`; `preview_scene()` builds bounds + feature size; GL upload in
  `src/structura/preview/gpu_scene.py` (pipelines `mesh, sphere, segments, triangles`; `u_mode` for segments,
  `u_width` in pixels, `u_fixed_radius` for spheres/dots; OIT split opaque/see-through).
- **Rendering**: `src/structura/render/pack.py` — `PackedScene.prim_f` (24 floats: `[0:12]` inverse affine,
  `[12:16]` rgba, `[16:23]` shape data, `[23]` generation), `prim_u` (4 ints: kind, material, source instance
  row, triangle row), `tri_f`; kinds dispatched through `render/kernels/scene.py` (`PRIM_F=24, PRIM_U=4`,
  `RK_BOX=0, RK_SPHERE=1, RK_CAPSULE=2, RK_TRIANGLE=3, RK_GRID=4`, solids `RK_ELLIPSOID/RK_CYLINDER/RK_TORUS =
  5/6/7`) and `render/kernels/solids.py` (analytic capsule/ellipsoid/cone/cylinder/torus hits).
- **Picking / provenance**: `src/structura/preview/pick.py`, `src/structura/ui/scene_view.py::describe_pick`,
  `src/structura/ui/panels/inspector.py`, `src/structura/ui/provenance.py`; outlines via the GPU id pass and
  CPU ray cast; “Same …” selections by rule/tag/generation/kind.
- **Reports**: `src/structura/render/report/data.py::by_kind`, `…/scene_sections.py::_triangles_per_instance`,
  `…/image_stats.py` (“Visible kinds”).
- **Stats/estimator**: `src/structura/core/lang/estimate.py` (per-rule expected object counts), build stats in
  `src/structura/services/build.py` / `src/structura/core/build/driver.py`.
- **Exporters**: `src/structura/export/legacy_obj.py::LEGACY_KINDS`, `…/scene/instancing.py::INSTANCED_KINDS`,
  `…/scene/affine_instances.py::AFFINE_KINDS/PARAM_KINDS`, `…/templates/engine.py::KIND_NAMES`,
  `…/scene/usd.py|gltf.py|gltf_instances.py|csg.py` — a knot kind must be consciously added to each of these
  lists or explicitly excluded.
- **Materials**: `src/structura/core/scene/material.py` (`Material`, `MaterialModel` with `PRINCIPLED,
  CONSTANT, WIREFRAME, AO, DEBUG_* , SHADOW_CATCHER`; `material_param_specs()` → the panel + write-to-script
  field source; debug models stay script-only), `materials.toml` presets, `material_look.py` (viewport
  approximation of glass/emission), `material_library.py`, `material_script.py::material_text/with_material`.
- **Lights / looks / camera / render**: `light_rigs.toml` + `light_rigs.py`, `light_script.py::KINDS`,
  `render/post.py::LOOKS`, `render/settings.py::INTEGRATORS/VIEWS`, `render/api.py::render`, camera blocks +
  `Copy camera to script`; render settings are `ParamSpec`-driven.

### 2.2 The knot-shaped gap (summary)

The feature needs, in order of dependency:

1. **A knot object in the scene** (kind + data + geometry + rendering + ray cast + pick + report + export).
2. **Knot text in EisenScript** (so a saved knot is a *structure* in the original script editor).
3. **The “Knots” dock panel UI** (editor, gallery, live preview, materials/lights/looks, save/open).

### 2.3 Files that a new primitive kind must touch (checklist, current state)

| Layer | Module | Change needed for a new kind |
|---|---|---|
| scene IR | `src/structura/core/scene/ir.py` | new `PrimitiveKind`, `LEGACY_KINDS` row, aux payload |
| builder | `src/structura/core/build/krules.py` | `emit`, `has_param`, aux row, constants |
| catalog | `src/structura/core/lang/catalog/primitives.toml` (+ `v2_blocks.toml` if script-visible) | new primitive / rule text |
| geometry | `src/structura/core/geometry/tessellate.py`, `v2_shapes.py`, `unit_shapes.py`, `triangles.py`, `trimesh.py` | kind → mesh; tube through beads |
| preview | `src/structura/preview/instances.py`, `gpu_scene.py`, `shaders/*` | batch + pipeline + `u_width` |
| compute | `src/structura/render/kernels/scene.py`, `kernels/solids.py`, `kernels/models.py` | `RK_*` hit + dispatch |
| render | `src/structura/render/pack.py`, `kernels/layout`, `kernels/emitters` | shape data + kind id |
| reports | `src/structura/render/report/*` | kind names / counts / “Visible kinds” |
| exports | `src/structura/export/*` (legacy_obj, instancing, affine_instances, templates, scene/*, csg) | kind lists / tessellation |
| inspector/pick | `src/structura/ui/panels/inspector.py`, `ui/scene_view.py`, `preview/pick.py`, `ui/provenance.py` | kind name, size, selection |
| language | `src/structura/core/lang/*` (estimate, catalog, v2 blocks, fixes, inlay, folding, reference, completion) | primitive known/registered; estimator counts |

---

## 3. What the KnotPlot material gives us (facts from `planning/knotplot`)

### 3.1 Research inventory

- `src/structura/planning/knotplot-detailed-feature-inventory.md` — 662 lines; sections 1–23:
  - §3 “Mathematical objects and underlying representations”: closed knots, multi-component links, open
    strings, braids, knotted graphs, polygonal (beads) vs smooth-tube representation, per-component
    attributes.
  - §4 “Catalogues, discovery, and loading”: >3,000-knot database claim, Rolfsen ~384 catalogue entries,
    `load 3.1`, zoos, specials, random.
  - §5 “Construction and procedural generation”: sketch, torus knots/links, Lissajous, Conway, tangle
    calculator, rational tangles, braids, constructors, additive mode, Turk’s head.
  - §6 “Celtic”; §7 “Editing, component management, and transformations” (beads/vertices, open/close,
    cut/join, delete, isolate, swap, reverse, shift, nbeads, split, identify, cable, double, companion,
    satellites, braid warp, anchors, undo); §8 “Geometric transformations”; §9 “Relaxation, dynamics…”;
  - §10 “Topology and geometric measurements” (Gauss, Dowker, Alexander, HOMFLY, writhe, ACN, thickness,
    Simon energy, info, coords); §11 “4D”; §12 “Viewing, rendering, and appearance” (modes, draw, matrgb,
    saturation/value, tube radius `cyl-rad`, `nseg`, `ncurve`, `cheapo`/`luxo`, `twfix`, grid, …); §13
    “Images, vector graphics, and publication output”; §14 “Surface-model export and interchange”; §15
    “Native files and data exchange”; §16 “Scripting, automation, and extensibility”; §17 “TopoICE”;
  - §18 “Educational, exploratory, and exhibition features”; §19 “User interface and learning support”
    (three-window layout, panels: Main, Display, Dyna, Sketch, Edit, Export, Comp, Surf, Cons, Cat, 4D,
    TopoICE); §20–§22 related/capabilities not established; §23 source map.
- Native file format (from `planning/knotplot/doc/html/FileFormats.html` and the binary samples):
  header begins with the string `KnotPlot 1.0`, ends with a control-L (newline-page) + one character; fields:
  `endf`, `comp`, `LOCF`, `LOCS`, `IDEN`, `VIEW`, `COMM`, `Attr`, `PGM`, `PPM` (+ more). Field-name case
  convention: lower-lower = null data segment; upper-upper = 4-byte length + that many bytes; upper-lower =
  4 bytes of data. `LOCF`/`LOCS`/`LOCC` are compact encodings; coordinates are 8-byte doubles.
- ASCII knot files (`planning/knotplot/demos/5cell.ascii`, `8cell.ascii`, `108cell.ascii`, `600cell.ascii`,
  …): free-text coordinate lists; exact row semantics of the leading integers still need a quick pass through
  the `coords` output before implementing a parser (flagged as an open item in §9).
- The knot material also includes exhibits, specials (e.g. `trefoil-cabled`, `EscherTrefoil`,
  `Tait-trefoil-monster`, `108cell`, `NotMonster.k`, `Perko1.kpm`, `SameDowkerGranny.k`, `UnknotFlowers.kps`,
  `spun-trefoil`, `unknot-stack*`, `rgs*` …), benchmarks, and a resource dir with `.knotplotrc`.

### 3.2 What the feature needs from KnotPlot (design inputs)

- Bead model: positions + connectivity (closed vs open) + per-component colour/width (KnotPlot `Attr` /
  `cyl-rad` / `hstart` / `auto-colour`).
- Smooth tube: `mode s`, tube radius, `nseg`, `ncurve`, `twfix`, `cheapo`/`luxo`.
- Gallery: catalogue index, specials, zoos, random, torus-knot families.
- Save: native knot save/load + ASCII coordinate exchange.
- Construction: sketch, torus, Lissajous, Conway, tangle, braid, constructors (useful later; not required for
  the first cut).

---

## 4. Constraints and design principles already mandated by the repo

From `PLAN.md`, `docs/17-code-standards-and-layout.md`, CI gates and ADRs:

- **Layers with one-way dependencies**; import-linter contracts (`lint-imports`) must stay green.
- **Qt only in `ui` (+ QtCore in `services`)**; knot domain code must stay Qt-free.
- **DRY**: one concept → one implementation; the viewport, CPU/GPU BLAS builder and exporters share
  `core/geometry/unit_shapes`, `beams`, `instanced`.
- **Every new setting is a `ParamSpec`**; size limits of `tools/check_sizes.py` (400 lines/module, 300/class,
  50/function, nesting 4).
- **Google docstrings** on changed definitions; `ruff`, `ruff format`, `mypy --strict`, `lint-imports`,
  `gen_reference --check`, `update_translations --check`, full pytest (core, UI, render, preview, golden) must
  stay green.
- **Registries instead of switch statements** (integrators, materials, lights, cameras, filters, samplers,
  bucket orders, exporters, themes, completions).
- **Long work runs on background lanes** (`services/jobs.py` JobRunner: compute / io / build lanes).

These constraints shape the knot implementation: the scene-kind work must be one pass through the geometry /
render / preview / export modules with registry-style extension, not scattered conditionals.

---

## 5. Design proposals

### 5.1 The knot object model (proposed)

A knot = a named collection of **components**; each component = a polyline of beads plus closure and visual
state.

```text
Knot {
  name: str
  components: tuple[KnotComponent, ...]
}
KnotComponent {
  beads: N × Vec3        # bead positions (object/world space as authored)
  closed: bool           # closure of the loop
  radius: float          # tube radius (KnotPlot: 'cyl-rad'; per-component width)
  rgba: (r, g, b, a)    # per-component colour (KnotPlot: 'hstart'/'auto-colour'/'Attr')
}
```

- Saved structures in the script editor then carry: beads + closure + radius + colour (and, for catalogue
  knots, the crossing-pair table when known).
- The scene-level row: `kind = PrimitiveKind.KNOT` (new), `xform` = the component’s transform, `rgba` = its
  colour, plus a per-component aux payload (beads; the plan prefers extending the param/aux tables or adding a
  dedicated aux table — an explicit decision for Phase 1).

### 5.2 The “Knots” dock panel — placement options

> **Owner clarification (2026-11-22):** the knot surface should be a **dock panel**, not a tab in the editor and
> not a third view tab. The placement decision in §5.2 has been updated accordingly.

| Option | What it is | Pros | Cons |
|---|---|---|---|
| (a) Dock panel (“Knots”) added to `ui/dock_layout.py::PANELS` | Side/rail panel hosting gallery + editor + preview + actions | **chosen placement** — fits existing panel architecture; no editor-stack surgery; the preview viewport can be dock-hosted | “feels like a panel” is accepted by owner decision; live preview is a dock-hosted viewport widget |
| (b) New view tab in the `views` QTabWidget (`Viewport / Render`) | Third tab “Knots” | literal “tab” wording | the view tab area is scene-view oriented; a knot editor is not a render view — **rejected** |
| (c) Synthetic `EditorTab` (generated knot script text) added to `DocumentTabs` | The knot surface as an editor tab whose text is generated knot EisenScript | reuses editor (highlighting, completion, lint, outline, params, build, preview, inspector, ancestry, save/close) nearly for free; “save as script” becomes trivial | **rejected** — owner clarified the knot surface must be a dock panel, not an editor tab; lifecycle/unsaved-save semantics would also need care |

**Recommendation (Phase 3, updated per the owner’s clarification):** implement **(a)** — a **dock panel** called
**“Knots”** added to the main window’s dock layout (`src/structura/ui/dock_layout.py::PANELS`) — as the single knot
surface. It hosts, in order: toolbar actions (New / Open / Save as Script / Random / Load), the picker gallery,
the knot editor, the live preview viewport, materials/lights/looks controls, and status/inspector read-outs.
The saved structure still lands in a **normal file-backed tab** via
`DocumentActions`/`ProjectActions` (`src/structura/ui/documents.py::EditorTab`,
`src/structura/ui/app_window.py::_layout`, `src/structura/ui/documents.py::DocumentTabs::add/open_file`) — that
part is unchanged, since “save as structure” means “emit knot text → file-backed tab”, which the dock panel
triggers through the ordinary document machinery. Options (b) and (c) are now **rejected** by owner decision;
option (a) is the only placement under active consideration.

### 5.3 The knot in EisenScript / the “saved structure”

- Saved structures must be ordinary EisenScript so the existing editor, compiler, preview, render, export and
  reports render them. Two candidate shapes (decision deferred to Phase 2, with recommendation):
  1. a new v2 primitive (`knot` / `knot[…]`) — best fit with `core/lang/catalog/primitives.toml` + resolver +
     estimator + completions; or
  2. a generated knot *rule/constructor* text emitted by the panel and saved into a script.
- The panel emits the knot text (beads, closure, radius, colour, material preset) and the user can paste/save it
  into a normal script; `material` blocks, `light`, `camera`, `render` blocks all already exist and are reused
  for the final render.

### 5.4 The picker gallery inputs

- Established knots: catalogue entries (`load 3.1` style, Rolfsen ~384) + specials + user library; planned
  source: curated TOML library (Phase 0) mirroring `core/scene/materials.toml` / `light_rigs.toml` patterns.
- Gallery UX: search (fuzzy `PickerPopup`-style ranking exists in `src/structura/ui/picker.py`), category filter,
  thumbnail grid (reuse `render/thumbnail.py::script_thumbnail` + `ExamplesPanel` caching), random pick,
  torus-knot family presets.

---

## 6. Implementation phases

| Phase | Content | Why now | Exit criteria |
|---|---|---|---|
| **0** | Knot library data: curated TOML entries + loader (`kots()`-style cache), initial curated set (trefoil, unknot, Perko pair, 5‑cell, Borromean, 3_1, granny, square, Tait‑trefoil‑monster, 108‑cell, 600‑cell, …) and a conversion path from the KnotPlot samples. | Pure data; de-risks everything downstream; no geometry code. | Library loads; counts/entries unit-tested; catalogue format fixed. |
| **1** | Scene kind `KNOT` end to end: IR + builder + aux, tessellation (smooth tube over beads), GL preview batch + shader (`u_width`), compute ray cast (`RK_KNOT`), render pack + kernels, emitters, reports, inspector/pick, stats; exports explicitly handle knots (OBJ curve/lines, PLY, …). | The spine; everything else consumes it. | A knot built through the new path renders in preview + precision render + exports; picking/report/stats work. |
| **2** | Knot as EisenScript text: catalog entry, script syntax, emitter (knot → script text), save-as-structure (`DocumentTabs` → file-backed tab), open-from-script round trip. | Without this the saved knots are not “structures in the original script editor”. | A saved knot script builds a knot scene; lint/completion/estimate/signature recognise it. |
| **3** | The **Knots** dock panel UI: panel/host composition, gallery widget, editor widget, live-preview wiring (Workbench build → viewport), materials/lights/looks controls, actions (Save as Script…, Open in Editor, Random, Load), commands (`view.panel.knot…`, menu entries), shortcuts, i18n (`tr`, catalogue, `gen_reference`, `update_translations`). | UI last: all domain primitives are stable before the surface is built. | Offscreen UI tests pass; live edit → rebuild → preview → save flow works. |
| **4** | Library completion & polish: gallery population from library + examples, thumbnails, categories, random, search ranking, knot-specific parameters (`#param`) and camera framing. | UX hardening. | Gallery at “large list” fidelity for curated set; live preview latency acceptable. |

**Phase order rationale:** data (0) → geometry/render (1) → language/save (2) → UI (3) → polish (4). This mirrors
the repo’s own “build the primitive before the panel” instinct and keeps each phase independently testable.

---

## 7. Materials, styles and looks — how the knot plugs into the existing program

- **Materials:** reuse `MaterialModel` (principled / constant / wireframe / ao / neon / …) and presets; per
  knot component colour + radius map to `scene.rgba` + knot radius; viewport approximation via
  `material_look.py`; “Write to Script” writes `material NAME { … }` blocks (`material_script.py`,
  `material_actions.py`).
- **Looks:** `render/post.py::LOOKS` (bloom, vignette, grading, LUTs) + Render-view look combo + script
  `render { look … }`; must apply to knot renders exactly as to other structures (same integrator, same
  settings path).
- **Lights:** `light_rigs.py` / `light_rigs.toml` / `light_script.py::KINDS` / `light_actions.py`; rigs are
  sized to the structure’s bounds — knot-aware (bounding box of a knot differs from a box).
- **Camera:** camera blocks, saved views, “Copy camera to script”, framing (`frame_all`).
- **Render/integrators:** `render/api.py::render`, integrators (`path`, `classic`, `preview`), ground, AOVs —
  all consumed through the packed knot scene unchanged.

---

## 8. Testing and quality gates (knot-specific additions)

- Unit: knot library parse; emitter text; scene-kind counts; tube tessellation (beads→mesh) correctness;
  ray cast through a knot; save-as-script text.
- Preview: GL-free compute preview pick on a knot; UI offscreen tests for the dock panel.
- Render: path-trace a knot (energy/bounce sanity), AOV pass; compare preview vs precision silhouette.
- UI: tests in `tests/ui/` (existing patterns: `test_tabs_and_frame.py`, `test_panels.py`, `test_sidebar.py`,
  `test_saving.py`).
- Golden: knot kinds are new, so legacy golden corpus is untouched; legacy export lists (`LEGACY_KINDS`) must
  stay unchanged for legacy scripts.
- Gates: `ruff`, `ruff format --check`, `mypy --strict`, `lint-imports`, `tools/check_sizes.py`,
  `gen_reference --check`, `update_translations --check`, full pytest.

---

## 9. Risks and open questions

1. **Topology safety:** editing/relaxation must not silently change knot type; collision-avoiding dynamics
   should be the default for knot relaxation.
2. **ASCII format ambiguity:** leading integers in `demos/*.ascii` need confirmation (coords/KnotPlot tooling)
   before a parser exists.
3. **Knot geometry fidelity:** Catmull-Rom smoothing vs linear bead segments; tube radius units (world units
   vs object units); `nseg`/`ncurve`/`twfix` behaviour for knots.
4. **Crossings / over-under:** catalogue knots may store crossing pairs; user-created knots derive them from
   the embedding — document the difference.
5. **Performance:** 3,000+ knot library; per-knot builds; thumbnails.
6. **Scope creep:** where knot measurements (Gauss/Dowker/poly) should live if at all (probably out of scope for
   the dock panel; KnotPlot owns those).

---

## 10. Non-goals (first cut)

- Molecular-dynamics / TopoICE solver features inside the dock panel.
- New export formats beyond what the existing exporters gain a knot kind.
- Full knot-theory tooling (classification, invariants) inside Structura (the panel).
- Any behaviour change to the existing EisenScript v1 / v2 language for *ordinary* structures (the knot
  work must be additive; legacy behaviour and the golden corpus stay untouched).

---

## 11. Exit criteria for the proposed plan

- The “Knots” dock panel delivers: edit → live preview → materials/looks → save-as-structure → open-in-editor,
  with all repo gates green and tests added.
- Saved knots render through the ordinary pipeline (`structura render`, export, reports).

---

## 12. References (source of truth)

- `src/structura/core/scene/ir.py`, `src/structura/core/build/krules.py`, `src/structura/core/lang/catalog/primitives.toml`
- `src/structura/core/geometry/tessellate.py`, `src/structura/core/geometry/v2_shapes.py`, `src/structura/core/geometry/trimesh.py`
- `src/structura/preview/instances.py`, `src/structura/preview/gpu_scene.py`, `src/structura/preview/shaders/segments.{vert,frag}`
- `src/structura/render/pack.py`, `src/structura/render/kernels/scene.py`, `src/structura/render/kernels/solids.py`, `src/structura/render/kernels/models.py`
- `src/structura/export/*`, `src/structura/render/report/*`
- `src/structura/ui/app_window.py`, `src/structura/ui/documents.py`, `src/structura/ui/workbench.py`, `src/structura/ui/panels/*`, `src/structura/ui/dock_layout.py`, `src/structura/ui/picker.py`
- `src/structura/core/scene/material.py`, `materials.toml`, `material_look.py`, `material_script.py`, `src/structura/core/scene/light_rigs.*`, `src/structura/core/scene/settings.py`, `src/structura/render/post.py`, `src/structura/render/settings.py`, `src/structura/render/api.py`, `src/structura/render/thumbnail.py`
- `src/structura/core/lang/*`, `src/structura/core/lang/catalog/*`, `src/structura/core/lang/v2/*`
- Planning/reference material: `src/structura/planning/knotplot-detailed-feature-inventory.md`, `src/structura/planning/knotplot/` (FileList, demos/*.ascii, special/, exhibits/, doc/html/FileFormats.html, resource/.knotplotrc)

---

## 13. Next step

Phase 0 is implemented (2026-11-23): the curated knot library (`src/structura/core/scene/knot_library.toml`
plus the `knots()` loader and the `Knot`/`KnotComponent` data), the first curated knots (trefoil, unknot) and
the unit tests — all green. The next concrete action is Phase 1 (the scene kind); the KnotPlot ASCII conversion
remains an open item (§9).

---

## 14. Change log

- **2026-11-22** — Owner clarified that the Knot **“tab”** should be a **dock panel**, not a tab in the editor and
  not a third view tab. Updated accordingly: §1 (restated request now says “dock panel”), §2.2 (“Knots” dock panel
  UI), §5.2 (placement decision — option **(a)** chosen, options (b)/(c) **rejected**, recommendation rewritten for
  the dock-panel host; saved structures still land in a normal file-backed editor tab via the ordinary document
  machinery), §6 Phase 3 (dock panel UI), §8 (offscreen tests for the panel), §10 (dock panel), §11 (dock panel),
  and §13. No source code was changed.
- **2026-11-23** — Phase 0 implemented: curated knot library (`knot_library.toml` + `knots()` loader + the
  `Knot`/`KnotComponent` data), first curated knots (trefoil, unknot), unit tests — ruff/format/check_sizes/
  pytest green; no geometry or UI code added yet (that is Phase 1).
