# 16 — Animation, Scripting & CLI

## 1. Goals

- Keep 1.5's `#javascript` movie scripts working unchanged.
- Offer a first-class **timeline** so most animations need no code at all.
- Provide a **Python API** and **CLI** for batch and farm use, built on the same domain functions as the GUI.

## 2. Timeline & keyframes

### 2.1 Model

```python
@dataclass(frozen=True)
class Timeline:
    fps: float = 30.0
    start: int = 1
    end: int = 240
    tracks: tuple[Track, ...] = ()

@dataclass(frozen=True)
class Track:
    target: TrackTarget          # PARAM(name) | CAMERA(field) | ENV(field) | LIGHT(name, field) | MATERIAL(name, field) | SEED | RENDER(field)
    keys: tuple[Key, ...]        # (frame, value, interpolation: CONSTANT | LINEAR | BEZIER, ease in/out)
```

- Any `#define … (float/int)` or `#param` can be keyframed from the Parameters panel (the ◆ toggle). So can
  the camera (eye/target/up/fov/aperture/focus), environment rotation and sun position, light and material
  fields, and the seed (stepped).
- v2 expressions can read `time`, `frame` and `fps` ([05](05-eisenscript-language.md) §9.1), which allows
  procedural animation without keys.
- The timeline is stored in the `.structura` project ([07](07-scene-model.md) §8).

### 2.2 Playback

- Scrubbing or playing evaluates the tracks. **Geometry-affecting** changes (params, seed, time in
  expressions) trigger a latest-wins build with the preview budget. **Non-geometry** changes (camera, env,
  materials) update immediately without rebuilding.
- **Frame cache:** an LRU of built `SceneIR`s keyed by the frame's program hash. Scrubbing back and forth is
  instant, and memory is capped. *(As built, M11: the workbench's SceneCache, docs/06 §10.5.)*

### 2.3 Animation render (Job)

```text
for frame in range(start, end+1):            # resumable: skips frames whose output exists (option)
    program = compile(analysis, params_at(frame), frame_vars(frame))
    scene   = build(program, seed_at(frame))          # build lane
    image   = render(scene, camera_at(frame), ...)    # device lane (CUDA/OpenCL/wgpu) or CPU lane
    write(image, pattern % frame)                      # io lane
```

- **Pipelining:** the build of frame n+1 overlaps the render of frame n (different lanes).
- Output: image sequences and/or video via imageio-ffmpeg ([15](15-export.md) §6).
- Motion blur is post-1.0 ([10](10-renderer-shading.md) §8).

## 3. Legacy `#javascript` compatibility (QJSEngine)

A script whose text starts with `#javascript` runs in a **`QJSEngine` on a dedicated script thread** (a
QThread owned by the scripting service). Script calls may block that thread, but never the GUI. Globals
mirror 1.5 exactly:

| Global | Members (1.5 semantics → Structura implementation) |
|--------|-----------------------------------------------------|
| `Builder` | `load(file)`: read an `.es` file relative to the script directory · `define(name, value)`: **raw substring replace** on all non-`#define` lines of the loaded system (1.5 quirk) · `prepend(text)`, `append(text)` · `build()`: compile + build synchronously on the script thread, then emit the scene to the viewport · `renderToFile(file, overwrite)`: offscreen viewport capture (requested from the GUI thread via signal; the script thread waits on an event) · `raytraceToFile(file, overwrite)`: render using the script's legacy settings (`classic` integrator by default; a preference can switch to the current render preset) · `templateRenderToFile(template, file, overwrite)`: legacy template export · `execute(program, args, waitForFinish)`: `QProcess`, confirmed once per session · `reset()`: restore the originally loaded text · `setSize(w, h)`: output size (0 keeps the aspect ratio) |
| `Debug` | `Info(text)` → Console · `Message(text)` → **non-modal** message panel (1.5 used a modal box) · `ShowProgress(caption)`, `SetProgress(0..1)`, `HideProgress()` → Job progress in the status bar · `Sleep(ms)` → sleeps the script thread · `waitForMouseButton()` → waits for a click in the viewport |
| `World` | `addSphere(center: Vector3, radius)`, `setColor(rgb: Vector3, alpha)`, `clear()`: direct scene edits, kept for the experimental 1.5 API |
| `Vector3` | Constructor `Vector3(x, y, z)` with `x/y/z` properties |

- Errors report "Uncaught exception at line N" exactly like 1.5, and also link to the line in the editor.
- Stop/Cancel interrupts the engine (`QJSEngine.setInterrupted(True)`).
- The three 1.5 JS examples in the corpus are part of the test suite.

> **As built (M11):** all four globals exist (`scripting/js_bridge.py`, `scripting/js_world.py`).
> `QJSEngine.evaluate` keeps Python's GIL while JavaScript runs, so a script thread inside the app would still
> freeze the window during a long pure-JavaScript loop. The window therefore runs `structura run --ipc` in a
> `QProcess` (`services/script_process.py`): the child prints channel lines (`info`, `message`, `progress`,
> `scene` as an `.npz` file, questions) that become signals, and reads yes/no answers on stdin
> (`Debug.waitForMouseButton` waits for a click in the viewport; `Builder.execute` asks once per command).
> `Builder.build` and `World` show their scenes in the viewport; Cancel kills the process. Headless
> `structura run` uses the same host without a channel (execute needs `--allow-execute`).

## 4. Python API (`structura.api`)

A small, stable, documented façade over the domain layer. It needs no Qt (except `run_legacy_js`, which
starts a `QCoreApplication`).

```python
import structura as st

doc = st.open("Nouveau.es")                       # Document: text, dialect, params, camera, render settings
doc.params["angle"] = 30
scene = doc.build(seed=7)                          # SceneIR (build_scene)
print(scene.stats.object_count)

img = st.render(scene, camera=doc.camera,
                settings=st.RenderSettings(integrator="path", samples=256, size=(1920, 1080)),
                device="auto")                     # "gpu" | "cpu" | "auto"
img.save("nouveau.exr")                            # metadata embedded

st.export(scene, "nouveau.usdc", format="usd", instancing="point-instancer", up_axis="Z")

for frame, scene in doc.animate(frames=range(1, 241)):
    st.render(scene, camera=doc.camera_at(frame)).save(f"out/frame_{frame:04}.png")
```

- Scripts can run inside the app via **Run Python Script…** (script thread, same API, with output to the
  Console) or outside with the CLI.
- The API surface is covered by docs and doctests. It follows semantic versioning from 1.0.

> **As built (M11):** `structura/api.py`, re-exported lazily by `import structura as st` (importing the
> package stays light): `st.build`, `st.render`, `st.export`, and `st.open(path)` → `Document` for a script or
> a project (`text`, `dialect`, `seed`, `params`, `camera`, `timeline`, `render_overrides`; `build(seed,
> frame)`, `animate(frames)` yielding `(frame, scene)` with the keyed parameters and seed, `camera_at(frame)`).
> `structura run file.py` runs a Python script; **Build ▸ Run Python Script…** runs one in its own process
> with its output in the Console. `structura animate` builds its Animation from the same Document.

## 5. Command-line interface

`structura` uses `argparse`. Subcommand flags are **generated from registry ParamSpecs**, so every render,
export and build option is available with identical names and defaults (DRY).

| Command | Purpose | Example |
|---------|---------|---------|
| `structura [FILE…]` | Launch the GUI (optionally opening files) | `structura Menger.es` |
| `structura lint FILE` | Diagnostics (text or `--json`); exit code 1 on errors | `structura lint *.es --json` |
| `structura build FILE` | Build and print stats; optional `--dump scene.npz` | `structura build tree.es --seed 3 --param angle=25` |
| `structura render FILE` | Render a still | `structura render city.es -o city.exr --size 3840x2160 --samples 1024 --device gpu --denoise` |
| `structura export FILE` | Export geometry or scene | `structura export city.es -f usd -o city.usdc --opt instancing=point-instancer` |
| `structura template FILE` | Legacy template export | `structura template city.es --template Sunflow-Colored -o city.sc` |
| `structura animate FILE` | Render the timeline | `structura animate spin.structura --frames 1-240 -o f_####.png --video spin.mp4` |
| `structura run SCRIPT` | Run `#javascript` or `.py` scripts headless | `structura run "JavaScript - Movie.es"` |
| `structura convert FILE --to v2` | Migrate v1 → v2 (defines → whole-word form made explicit, `set raytracer::*` → `render {}`/`material` blocks); prints a review diff | `structura convert old.es --to v2 -o new.es` |
| `structura theme {list,check,import}` | Theme tools ([13](13-theming.md)) | `structura theme import MyTheme.json` |
| `structura devices` | List compute adapters and limits | |
| `structura warmup` | Precompile Numba kernels and WGSL pipelines | (run by installers) |

> **As built (M10):** every command above exists. `theme` has `list`, `check [--strict]` and `import`;
> `devices` lists the compute backends (the same probe as `doctor`); `template` is `export --format template`
> with 1.5's wording; `structura FILE…` (or no arguments) starts the GUI. Added: `structura doctor` (Qt
> platform, OpenGL probe including XWayland, compute devices), `render --report FILE` (repeatable; `.pdf
> .html .md .txt .json .csv .odt`) and `export --preset NAME`.

Conventions:

- Progress goes to stderr (a TTY bar, or JSON lines with `--progress json`). Results go to stdout.
- Exit codes: 0 = success, 1 = script errors, 2 = usage error, 3 = device or resource error, 130 = cancelled.
- `--device auto` falls back to the CPU with a warning on stderr, so behaviour matches the GUI.

## 6. Module breakdown

```
structura/scripting/
  api.py               # public façade re-exported by structura/__init__.py
  document.py          # Document: open/params/camera/timeline helpers
  animation.py         # Timeline evaluation, frame vars, interpolation
  legacy_js/
    engine.py          # QJSEngine setup on the script thread
    builder_object.py  debug_object.py  world_object.py  vector3.py
  python_runner.py     # in-app Python script execution
structura/cli/
  main.py  commands/{lint,build,render,export,template,animate,run,convert,theme,devices,warmup}.py
  paramspec_argparse.py   # ParamSpec → argparse generator
```
