# TASK_STATE — clean-code review of the uncommitted branch changes

Resumable state for the review task (brief: "01–05", four critic cycles, 100-point rubric, exit ≥ 90 with
≥ 85 % per dimension, zero critical failures, code compiles and passes tests). **Nothing is committed.**

## Scope

The uncommitted changes of the working tree (`git diff` + untracked files): 143 changed/new Python files
under `src/`, 43 under `tests/`, 4 under `tools/`. Criticism targets changed code only; pre-existing code is
out of scope unless a change depends on it.

## Environment and commands

- `source /tmp/env.sh` (LD_LIBRARY_PATH for libOpenGL, `QT_QPA_PLATFORM=offscreen`, the `.venv` on PATH).
- Gates: `ruff check src tests tools`, `ruff format --check src tests tools`, `mypy`, `lint-imports`,
  `python tools/check_sizes.py`, `python tools/gen_reference.py --check`, `python tools/update_translations.py --check`.
- Long runs must be detached (the shell tool stops at 300 s and kills its children):
  `setsid nohup bash -c 'source /tmp/env.sh; pytest … > /tmp/log 2>&1; echo EXIT $? >> /tmp/log' &`
- Review helpers (outside the repo, /tmp/review): `scope.py` (changed definitions), `docs_check.py` (Google
  docstring sections of changed definitions), `dupes.py` (repeated statement windows touching changed code),
  `linecov.py` (stdlib `sys.monitoring` line coverage plugin: `PYTHONPATH=/tmp/review pytest -p linecov`) and
  `covreport.py` (coverage of changed lines). No new packages were installed for the review.
- Research: the official docs sites (doc.qt.io, google.github.io) are not reachable from this sandbox; the
  installed PySide6 stubs/docstrings and the Python stdlib docs (`pydoc`) were used instead.

## Last successful commands (newest first)

- Cycle 4 (final): `ruff check`, `ruff format --check`, `mypy` (460 files, no issues), `lint-imports` (2 kept),
  `check_sizes` (0), `gen_reference --check`, `update_translations --check` — all green. Core suite
  (`pytest tests --ignore=tests/ui --ignore=tests/golden`): 772 passed / 21 skipped (CUDA/GPU and v1-only
  skips; 9 min 56 s). UI suite (`pytest tests/ui`): 301 passed (11 min 18 s), no hang. Golden
  (`pytest -m golden tests/golden`): 943 passed.
  `docs_check.py`: 0/658 changed definitions (src, tools) and 0/186 (tests) without Google docstrings.
  Changed-line coverage (core + UI runs with `linecov`): 3300/3596 = 91.8 %.
- Cycle 2: all gates green (`ruff`, `ruff format --check`, `check_sizes`, `lint-imports`, `gen_reference --check`,
  `update_translations --check`; `mypy` green after the pack/ground/emitters import fix).
- Cycle 1: core 770 passed / 19 skipped (12 min, with the coverage plugin); UI 295 passed (11 min);
  render + parity 193 passed / 13 skipped.

## Baseline (before cycle 1)

- Last full green run (before this task): gates all green; core 760 passed / 19 skipped; UI 294 passed;
  golden 943 passed; Python 3.12 subset 700 passed.
- `docs_check.py src tools`: 598 changed definitions, 439 with Google-docstring problems (204 without a
  docstring, 63 classes without one, ~170 without Args/Returns sections).
- `dupes.py 4`: 3 repeated windows touching changed code (2 pre-existing exporter ParamSpec rows).

## Rubric score

| Cycle | Architecture /40 | DRY /30 | Docs /20 | Testing /10 | Total | Notes |
|-------|------------------|---------|----------|-------------|-------|-------|
| baseline | 33 | 25 | 9 | 7 | 74 | docstrings far from Google standard |
| 1 | 35 | 27 | 18 | 9 | 89 | improved (all four); 0/647 changed definitions without Google docstrings; a test-suite deadlock fixed |
| 2 | 36 | 28 | 19 | 9 | 92 | improved (+3): post split, light controller split, shared v2/build guards, display failures reported |
| 3 | 36 | 28 | 19 | 9 | 92 | unchanged total, testing deeper: NaN LUT, backups, GL probe fallback, second-instance race, the watchdog deadlock (#56); changed-line coverage 91.8 % |
| 4 | 37 | 28 | 19 | 9 | 93 | improved (+1): watchdog stacks read natively (no cross-thread frame ownership); informative Args; every changed definition documented |

Exit check after cycle 4: total 93 ≥ 90; Architecture 37/40 (92.5 %), DRY 28/30 (93 %), Docs 19/20 (95 %),
Testing 9/10 (90 %) — each ≥ 85 %; no open critical finding (#1 and #56 fixed); code compiles (mypy, ruff) and
both suites pass. **Exit criteria met. Nothing committed.**

## Findings log

Severity: critical (breaks use or tests), major (wrong behaviour in a realistic case), minor, info (noted,
out of scope). Status: F = fixed (with a test where behaviour changed), N = noted only.

### Cycle 1 — full read of the changed code by all four critics

| # | Critic | Sev. | Subsystem | Criticism → root cause → correction | St. |
|---|--------|------|-----------|--------------------------------------|-----|
| 1 | Tester | critical | ui.watchdog (UI suite) | UI suite hung at random (seen twice) → the sampler thread's target was a bound method of the QObject; when the thread dropped the last reference, PySide destroyed the QObject off the GUI thread (Qt connection lock, then GIL) while the GUI thread held the GIL and waited for that lock → plain `_Beat` state + module-level `_sample`, `stop()` joins; test `test_the_sampler_thread_never_owns_the_watchdog` | F |
| 2 | Tester | major | render.post | a missing or malformed LUT raised during display/save → the look must never stop an image → skipped with a logged warning (once per path) + test | F |
| 3 | Tester | major | services.session | one malformed tab made `from_json` fail, losing the whole recovery → per-tab `_tab()` tolerant parse + test | F |
| 4 | Tester | major | services.session | a crashed run's PID reused by another program hid the crash → `_is_structura(pid)` checks the command line + test (existing test marks its stand-in process) | F |
| 5 | Tester | major | ui.session_actions | malformed extras (params, views, timeline) could crash start-up restore → `_apply_extras` tolerant, logged | F |
| 6 | Tester | major | compute / services.render / cli | a raising `backend.details()` (driver) failed the render it only describes → `device_details()` wrapper + test | F |
| 7 | Tester | minor | core.scene.lens | `amount_for_fstop(≤0/inf)` math error, `focal_length_mm(0/180°)` ÷0, non-positive sensors accepted → guards + test | F |
| 8 | Tester | minor | core.scene.camera | `basis` NaN when up ∥ view direction → fallback axis + test | F |
| 9 | Tester | minor | export.mesh.mlp | two group keys with the same safe name overwrote one PLY → `unique_names` + test | F |
| 10 | Tester | minor | export.mesh.meshlab | empty mesh / unknown preset gave PyMeshLab or KeyError failures → explicit results/ValueError + test | F |
| 11 | Tester | minor | core.animation.paths | `frames_each ≤ 0`, zero-frame turntables → clamped / empty + test | F |
| 12 | Tester | minor | cli.animate | `--zoom ≤ 0` collapsed the camera onto its target → `_positive` argparse type | F |
| 13 | Tester | minor | render.declarations | `size 0x0` gave a zero-size render → clamped to ≥ 1 | F |
| 14 | Tester | minor | services.render | a failing re-tone-map job was silently dropped → `failed` connected | F |
| 15 | Tester | minor | core.project.model | a malformed `fov_y_deg` raised on load → `_float` fallback | F |
| 16 | Tester | minor | tools.fetch_fonts | a missing archive member crashed instead of trying npm → caught | F |
| 17 | DRY | major | render.post / cli / reports | reproduce commands dropped temperature, saturation, contrast, threshold, radius (CLI listed only some keys by hand) → one option per `post.RANGES` key with catalogue help, shared `look_arguments`; round-trip test | F |
| 18 | DRY | minor | core.scene.lens / camera | mm → world units written out 4× → `Lens.world()` | F |
| 19 | DRY | minor | core.color.values | two parsers of the same colour forms → `linear_of` built on `rgb_of` | F |
| 20 | DRY | minor | ui.viewport.orbit / core.animation.paths | Rodrigues rotation twice → `core.scene.vectors.rotate` | F |
| 21 | DRY | minor | render.post | Rec. 709 weights redefined → `views.LUMA` | F |
| 22 | DRY | minor | render.kernels | material-model constants scattered over 3 kernel files → `layout.MODEL_*` + test against `MaterialModel` | F |
| 23 | DRY | minor | render.pack / api / kernels | generation slot `23` ×3, PRIM_F/RK_* redefined in pack → `PF_GENERATION`, one definition in kernels.scene/solids | F |
| 24 | DRY | minor | render.details | light values re-formatted by hand → `block_form.value_text` | F |
| 25 | DRY | minor | core.project.model | `_vec3` = `vec3_of` → `vec3_of` | F |
| 26 | DRY | minor | core.scene.material_script | own number formatting; dead `material_fields` (= FIELD_NAMES) → `vectors.number`, removed | F |
| 27 | DRY | minor | render.config / render.api | radius and the AOV condition computed twice → once | F |
| 28 | DRY | minor | services.render / cli.render | backend label formatted 3× → `device_label()` | F |
| 29 | DRY | minor | cli.animate / services.animation | frame saving duplicated and every frame tone-mapped twice for videos → `save_frame()`, `save_image` returns the 8-bit image | F |
| 30 | DRY | minor | ui | spin/combo factories in 4 places → `ui/widgets/fields.py` | F |
| 31 | DRY | minor | ui.export_actions / external_apps | Blender-only wrappers duplicating the generic app path → removed | F |
| 32 | DRY | minor | ui | `to_display` called beside `Display` → `Display.apply` | F |
| 33 | DRY | minor | render.report.render_sections | `_vec` wrapper, `_count` = Counter → removed | F |
| 34 | DRY | minor | ui.session_actions | declined-recovery path built twice → `_declined` | F |
| 35 | Arch | minor | render.report.collect | `_shown_with` outside its data class → `ReportInputs.shown` | F |
| 36 | Arch | minor | core.scene.light_rigs / camera_block | one function per concern → `_sun_entries`/`_placed_entries`, `_lens_key` | F |
| 37 | Arch | minor | ui.dialogs.turntable_dialog | 50-line `__init__` → fields + `_layout()` | F |
| 38 | Arch | info | ui | 30 window controllers repeat `super().__init__(window); self.w = window` — pre-existing pattern in unchanged files too; a base class would touch them all → out of scope | N |
| 39 | Arch/DRY | info | export, render | pre-existing repeats (exporters' lod/unit_scale specs, Rec. 709 in emitters/report, #version regexes) → out of scope | N |
| 40 | Docs | major | all changed code | 439 of 598 changed definitions without Google docstrings (Args/Returns/Raises, Attributes) → written for every changed definition (src, tools, test helpers); dataclass field comments moved into Attributes | F |
| 41 | Docs | minor | export.base / compute.base | overrides had no documented base → `Exporter.write`, `Backend` protocol documented | F |
| 42 | Docs | minor | ui | two verbose/split comments → rewritten | F |

### Cycle 2 — the critics on the cycle-1 changes (regression check: improved)

| # | Critic | Sev. | Subsystem | Criticism → root cause → correction | St. |
|---|--------|------|-----------|--------------------------------------|-----|
| 43 | Arch | minor | render.post | cycle 1 left settings, parsing, CLI spelling and image operations in one 290-line module → image operations moved to `render/post_image.py` (settings stay in `render/post.py`) | F |
| 44 | Arch | minor | ui.material_actions | the Lights panel's controller lived in the Materials module → `ui/light_actions.py` | F |
| 45 | DRY | minor | ui | "convert this script to v2 first?" asked twice with copied code → `EditorActions.ensure_v2()` | F |
| 46 | DRY | minor | ui | "Build the script first (F5), then …" guard repeated in 4 actions → `MainWindow.built_tab()` | F |
| 47 | Tester | minor | services.render / render_view | a failed re-tone-map reported "Render failed" (or nothing) → `display_failed` signal: the picture stays, the status bar says why + test | F |
| 48 | Tester | minor | ui.session_actions / cli.animate | the cycle-1 guards had no tests → malformed-extras restore test, `--zoom 0` test | F |
| 49 | Tester | info | coverage | the first coverage numbers mixed runs made before the edits (line numbers moved) → fresh runs of both suites after cycle 2 | F |

### Cycle 3 — the Defensive Tester probes odd inputs of the new code; coverage re-measured

| # | Critic | Sev. | Subsystem | Criticism → root cause → correction | St. |
|---|--------|------|-----------|--------------------------------------|-----|
| 50 | Tester | major | render.lut | a NaN pixel (a broken sample) made `apply_lut` index the table with INT_MIN → IndexError while showing or saving → NaN reads as 0 + test | F |
| 51 | Tester | minor | services.backups | two saves within one second overwrote that second's backup with the newer text (the older version was lost) → keep the first + test | F |
| 52 | Tester | minor | ui.viewport.gl_probe / banners | the hidden-window fallback and the banner's Details / Use OpenGL anyway had no tests → fake-context test, banner test | F |
| 53 | Tester | minor | ui.editor_actions / app_window | the decline path of `ensure_v2` and the `built_tab` message were untested → test | F |
| 54 | Tester | minor | tests/services | the second-instance test raced the child's exec (right after fork the child still shows the parent's command line) → `_wait_for_exec` | F |
| 55 | Tester | info | review tooling | the coverage plugin started after conftest imports, so module-level lines counted as missed → monitoring starts at import | F |
| 56 | Tester | critical | ui.watchdog (UI suite) | the UI suite hung again (theme-editor test): the sampler thread took `sys._current_frames()`, so it held the GUI thread's frame objects; once the GUI thread had returned from them, the sampler dropped the last reference and the frames' locals (a PySide signal connection) were destroyed on the sampler thread — `QObject::disconnect` → Shiboken override lookup → GIL, while the GUI thread held the GIL and waited for Qt's connection lock (native stacks taken with eu-stack) → the stack is read through `faulthandler.dump_traceback` (walks interpreter frames natively, no frame objects change threads) and reformatted oldest-first as `traceback.format_stack`; test `test_a_thread_stack_reads_like_traceback_oldest_call_first` | F |

Regression check (cycle 3): improved — 7 defects fixed, one of them critical (#56, found by re-running the UI
suite under coverage); no regressions from cycle 2.

### Cycle 4 — final pass of all four critics on the cycle-3 changes (regression check: improved)

| # | Critic | Sev. | Subsystem | Criticism → root cause → correction | St. |
|---|--------|------|-----------|--------------------------------------|-----|
| 57 | Comment Nazi | minor | compute, export, core, preview, ui, tools | ~20 Args entries restated the name ("camera: The camera.") → each says what the argument is for or what is done with it | F |
| 58 | Comment Nazi | minor | ui actions, UI tests | 5 definitions touched in cycles 2–3 (`AnimationActions.render`, the `EditorActions` class, `LightActions.remove`/`go_to`, `MaterialActions.apply`) and 8 test fakes/helpers had no docstring → written (docs_check: 0/658 src+tools, 0/186 tests) | F |
| 59 | Architect | minor | ui.watchdog | the #56 fix must not change what the UI fixture parses → `_thread_stack` returns `traceback.format_stack`'s format, oldest call first; the faulthandler 100-frame cap (it keeps the innermost calls, which hold the culprit) documented | F |
| 60 | Tester | minor | tests/ui (timing) | `test_a_large_image_is_tone_mapped_off_the_gui_thread` timed out once (30 s wait for the compute-lane tone map) in the full UI run under the coverage plugin; it passes alone, with its neighbouring files under coverage, and in the full plain run (301 passed) → CPU/GIL contention under tracing, not a code defect; recorded under Known failures | N |
| 61 | DRY | info | ui, cli | `dupes.py 4` now also matches 4-statement `__init__` prologues (docstring, `super().__init__`, `self.w = window`) and `register()` openings — the pattern of #38; no shared code to extract | N |
| 62 | Tester | info | review tooling | `setdoc.py` put a docstring between a decorator and its `def` (a syntax error caught by ruff at once) → the tool inserts above the decorators | F |

Regression check (cycle 4): improved — documentation gaps closed, the watchdog fix reviewed; no regressions
(all gates, UI 301 passed, core suite below).

## Known failures

None at baseline. None open at the end of cycle 4. One timing flake seen (#60):
`tests/ui/test_render_settings.py::test_a_large_image_is_tone_mapped_off_the_gui_thread` timed out once in the
full UI run under the coverage plugin (sys.monitoring slows every thread); it passed in every run without it.
