# 17 — Code Standards & Repository Layout

This document turns the brief's principles into enforceable rules:

- **DRY**;
- **small files, functions and classes**;
- **non-blocking with Qt signals/slots**;
- **GPU + CPU**.

Each rule lists the mechanism that enforces it.

## 1. Size limits

| Unit | Soft limit | Hard limit (CI fails) | Enforced by |
|------|-----------|------------------------|-------------|
| Module (file) | 250 lines | **400 lines** | `tools/check_sizes.py` (counts non-blank, non-comment lines) |
| Function / method | 30 lines | **50 lines** | ruff `PLR0915` (statements) + `check_sizes.py` (lines) |
| Class | 200 lines, ≤ 12 public methods | **300 lines**, ≤ 20 public methods | `check_sizes.py`, ruff `PLR0904` |
| Cyclomatic complexity | 8 | **12** | ruff `C901` |
| Parameters | 5 | **7** (use a dataclass beyond that) | ruff `PLR0913` |
| Nesting depth | 3 | **4** | `check_sizes.py` |
| Branches per function | 8 | **12** | ruff `PLR0912` |

- Exceptions need an inline `# size-exempt: <reason>` comment and reviewer approval. They are reported in
  CI and tracked (the target is zero at 1.0).
- Generated code (SKL output, Qt resource files) is exempt by path.
- For scale: the largest 1.5 files were `MainWindow.cpp` (1,791 lines) and `TemplateExportDialog.cpp`
  (1,149). Under these rules, their successors are split into about 20 and about 6 modules.

## 2. DRY rules

1. **One definition per concept.** The table below is normative. Introducing a second implementation of
   any listed concept is a review blocker.

| Concept | Single source |
|---------|---------------|
| EisenScript keywords, operators, `set` keys, colours, diagnostics, snippets | `core/lang/catalog/*.toml` |
| Lexing (parser + highlighter) | `core/lang/lexer.py` |
| Unit primitive geometry | `core/geometry/unit_shapes.py` |
| sRGB ↔ linear, HSV, QColor semantics | `core/color/` |
| Camera maths, view transforms | SKL modules in `kernels/shared/` |
| GPU/CPU kernels | SKL sources (`*.skl.py`) |
| Buffer layouts | SKL `@struct` → numpy dtype + WGSL ([11](11-compute-backends.md) §2) |
| Settings (UI forms, CLI flags, serialisation, validation, completion) | `ParamSpec` tables per registry |
| Actions (menus, toolbar, palette, shortcuts) | `ui/commands/registry.py` |
| Background work | `services/jobs/` (Job framework) |
| Theme colours | Semantic roles + `themes/derive.py` |
| Export scene conversion (camera, lights, materials, axis) | `export/scene_model.py` |

2. **Data over code.** Prefer tables (TOML/dataclasses) plus a small interpreter over parallel if/else
   chains. Structure Synth's `EisenParser::transformation()` (16 near-identical branches) becomes one operator
   table and one generic argument parser.
3. **Rule of three for helpers.** Extract on the second duplication if the code is non-trivial, and always on
   the third.
4. **Generated artefacts are never edited by hand.** This covers the language reference, CLI help,
   diagnostics docs, theme role docs and WGSL. CI regenerates them and fails if they differ.

## 3. Typing & style

- Python 3.12 syntax (PEP 695 generics allowed; `type` aliases; `match` where clearer).
- **`mypy --strict`** on all packages except generated code. `typing.Protocol` for backends, exporters and
  services. `@dataclass(frozen=True, slots=True)` for value objects.
- numpy arrays are annotated with `numpy.typing.NDArray[np.float32]` and so on. Shapes are documented in the
  docstring (`(N, 3, 4)`).
- **ruff** for lint and format (line length 120, double quotes, isort-compatible import order). Selected rule
  sets: `E,F,W,I,N,UP,B,C4,SIM,PL,RUF,D` (pydocstyle, Google convention) and `C90` (complexity).
- Naming: modules `snake_case`; classes `PascalCase`; Qt signals `snake_case` past tense (`build_finished`);
  slots `on_<source>_<signal>`.
- Docstrings on every public function and class. SKL functions document their units and spaces
  (world/object, radians/degrees).

## 4. Qt & concurrency rules (lint-checked where possible)

| Rule | Check |
|------|-------|
| No `QApplication.processEvents()` anywhere | ruff banned-api |
| No `time.sleep`, `.join()`, `.result()`, blocking `map` on the GUI thread | Custom AST lint on `structura/ui/**`; runtime UI-stall watchdog in tests |
| No `QtWidgets` import outside `ui/` and `app/` | import-linter |
| No Qt import in domain packages | import-linter |
| Signals carry immutable payloads only | Review checklist + `freeze()` helper for numpy arrays |
| Cross-thread communication via signals/slots only (queued) | Review + tests that assert thread affinity |
| New background work must be a `Job` | banned-api for `threading.Thread`, `concurrent.futures` outside `services/jobs/` |

## 5. Error handling & logging

- Domain code raises `StructuraError` subclasses, never bare `Exception`. Messages are user-facing, with an
  optional `hint`.
- Never swallow exceptions silently. Either handle them with a logged reason or let them propagate to the
  Job boundary.
- `logging.getLogger(__name__)` everywhere. No `print` outside the CLI output layer.

## 6. Repository layout

```
Structura/
├── pyproject.toml              # deps, ruff, mypy, import-linter contracts, entry points
├── uv.lock
├── README.md  LICENSE (MIT)  THIRD_PARTY_NOTICES.md  CHANGELOG.md
├── docs/                       # ← this planning set; later also user & developer guides
├── sample_source/              # legacy sources (read-only reference; excluded from the wheel)
├── tools/
│   ├── check_sizes.py          # size/nesting limits
│   ├── gen_docs.py             # language reference, diagnostics, CLI, roles from catalogues
│   ├── golden/                 # C++ harness + Qt5 build to produce golden outputs from 1.5 (test-only, GPL)
│   ├── brand/                  # logo generator
│   └── bench/                  # benchmark scenes & runners
├── src/structura/
│   ├── resources/              # package data (shipped in the wheel)
│   │   ├── brand/              # generated by tools/brand (logo, icons)  [21]
│   │   ├── fonts/              # Inter, JetBrains Mono (OFL)
│   │   ├── legacy/             # Structure Synth 1.5 templates + examples, unmodified (LGPL/GPL data)
│   │   ├── examples/community/ # MIT community samples
│   │   └── hdri/  icons/  templates/ (new-style templates)
│   ├── __init__.py             # re-exports structura.api
│   ├── app/                    # GUI bootstrap, splash, warm-up
│   ├── cli/                    # [16]
│   ├── core/
│   │   ├── registry.py  paramspec.py  errors.py
│   │   ├── math/               # affine.py, vec.py
│   │   ├── color/              # srgb.py, hsv_legacy.py, qcolor_compat.py, names.py, oklch.py
│   │   ├── rng/                # mt19937.py, pcg.py, sobol_tables.py
│   │   ├── lang/               # [06]
│   │   │   ├── api.py  source.py  preprocess_legacy.py  preprocess_v2.py  lexer.py
│   │   │   ├── parser/         # one module per production group: program.py, rules.py, actions.py, transforms.py, sets.py, v2_blocks.py, expr.py, recovery.py
│   │   │   ├── cst.py  ast.py  semantic.py  resolve.py  estimate.py
│   │   │   ├── lint/           # rules/*.py (one lint per file), runner.py
│   │   │   ├── compile/        # tables.py, transforms.py, colorops.py, setops.py, pools.py
│   │   │   ├── format/         # printer.py
│   │   │   └── catalog/        # *.toml + loader.py
│   │   ├── build/              # api.py, kernel.py, state.py, emit.py, driver.py, stats.py, trace.py
│   │   ├── scene/              # ir.py, materials.py, lights.py, camera.py, settings.py, provenance.py, project.py, project_migrations.py
│   │   └── geometry/           # unit_shapes.py, tessellate.py, affine.py, weld.py, lod.py, bounds.py
│   ├── kernels/
│   │   ├── skl/                # [11] compiler
│   │   └── shared/             # camera.skl.py, color.skl.py, view_transform.skl.py, hash.skl.py
│   ├── compute/                # backends: cuda.py, opencl.py, wgpu.py, cpu.py, select.py, device_lane.py, limits.py
│   ├── render/                 # [09] [10]
│   ├── preview/                # [08] GLSL/OpenGL preview engine + Numba fallback
│   ├── export/                 # [15]
│   ├── scripting/              # [16]
│   ├── themes/                 # roles.toml, model.py, derive.py, contrast.py, loaders/{toml,vscode,base16}.py, builtin/*.toml
│   ├── services/
│   │   ├── jobs/               # job.py, context.py, runner.py, lanes.py, handle.py, watchdog.py
│   │   ├── document.py  project.py  build.py  render.py  export.py  language/  theme.py  settings.py  scripting.py
│   └── ui/                     # [12] [14]
└── tests/
    ├── unit/ (mirrors src tree)   ├── golden/ (corpus + expected outputs)
    ├── parity/ (GPU vs CPU)       ├── render_regression/
    ├── ui/ (pytest-qt)            ├── perf/ (pytest-benchmark)
    └── conftest.py
```

## 7. Version control & review

- Trunk-based development with short-lived branches. PRs must pass all CI gates ([18](18-testing-and-quality.md)).
- Conventional commits (`feat(lang): …`, `fix(render): …`) drive the changelog.
- Every PR touching a DRY table (§2) or an SKL kernel needs a second reviewer from the owning area.
- ADRs are required for new dependencies, new layers or packages, and any deviation from these standards
  ([adr/README.md](adr/README.md)).

## 8. Definition of Done (per feature)

1. Code meets §1–§5; CI is green (lint, types, contracts, sizes, tests, parity where relevant).
2. Unit tests and, where applicable, golden, parity, UI or perf tests have been added.
3. User-visible strings are translatable, and docs and catalogues are updated (generated docs regenerated).
4. No GUI-thread stall > 50 ms in the feature's UI test (watchdog).
5. Both GPU and CPU paths are exercised (if the feature touches rendering or the viewport).
