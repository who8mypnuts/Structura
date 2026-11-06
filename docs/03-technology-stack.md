# 03 — Technology Stack

The brief says additional dependencies are **required, never optional**, and features must be the same on
every platform. So every package below is a hard install requirement with wheels on Windows x64, macOS
(arm64 + x86-64), and Linux x86-64/aarch64. Nothing is imported lazily to hide a missing feature.

## 1. Language & runtime

| Item | Choice | Notes |
|------|--------|-------|
| Python | **3.12** baseline; CI also runs **3.13** | 3.12 has the broadest wheel coverage across the stack below. Free-threaded 3.13t is tracked ([20](20-risks.md)) but not targeted. |
| Packaging | `pyproject.toml` + **hatchling**; environments via **uv** | A lock file (`uv.lock`) is committed |
| App bundles | **PyInstaller** (one-folder) → MSIX/MSI (Windows), notarised DMG (macOS), AppImage + Flatpak (Linux) | Numba caches are pre-warmed at install time ([11](11-compute-backends.md) §7) |

## 2. Runtime dependencies (all required)

| Package | Min version policy | Licence | Used for | Why it is required |
|---------|--------------------|---------|----------|--------------------|
| **PySide6** (QtCore, QtGui, QtWidgets, QtSvg, QtQml) | ≥ 6.8 | LGPL-3.0 | UI, signals/slots, threads, `QSyntaxHighlighter`, `QJSEngine` for legacy `#javascript` | Mandated by the brief; QtQml gives a JS engine at no extra cost |
| **numpy** | ≥ 2.0 | BSD-3 | SceneIR arrays, tessellation, packing, I/O | The foundation of the data-oriented design |
| **numba** (+ llvmlite) | ≥ 0.61 | BSD-2 | CPU kernels: builder, BVH build, CPU renderer, tessellation hot loops | Multithreaded (`prange`), releases the GIL (`nogil=True`), and can run the *same* SKL source as the GPU ([11](11-compute-backends.md)) |
| **ModernGL** | ≥ 5.12 | MIT | Preview engine: OpenGL 3.3/4.1 core + GLSL on Qt's `QOpenGLWidget` context | The lightest, most reliable modern-GL binding for Python; it attaches to Qt's context ([ADR-0013](adr/0013-two-render-engines.md)) |
| **cuda-python** + **nvidia-cuda-nvrtc-cu12** | latest 12.x / 13.x | NVIDIA (verify redistribution terms) | Precision engine **CUDA** backend: driver API + runtime compilation of SKL-emitted CUDA C | Fastest backend on the reference GTX 1660. Installed on Windows/Linux (environment marker); CUDA does not exist on macOS. |
| **pyopencl** + **pocl-binary-distribution** | ≥ 2024.2 | MIT / MIT | Precision engine **OpenCL** backend (AMD/Intel/NVIDIA GPUs); pocl supplies a CPU OpenCL device on every machine | Vendor-neutral GPU compute; pocl makes OpenCL testable without a GPU |
| **wgpu** (wgpu-py) | exact minor pin | BSD-2 | Precision engine **WGSL** backend (offscreen compute over Vulkan / Metal / D3D12 / GL) | The only GPU-compute path on macOS; a universal fallback elsewhere |
| **usd-core** | ≥ 24.11 | Modified Apache-2.0 (Pixar) | USD export: `.usda`, `.usdc`, `.usdz`; `PointInstancer`, `UsdPreviewSurface` | The only complete USD writer; the brief requires USD |
| **pygltflib** | ≥ 1.16 | MIT | glTF 2.0 / GLB, including `EXT_mesh_gpu_instancing` and `KHR_materials_*` | A correct glTF container at low cost |
| **manifold3d** | ≥ 3.0 | Apache-2.0 | Robust mesh booleans: watertight union for STL/3MF printing; CSG groups | Reliable booleans are hard to write ourselves |
| **Pillow** | ≥ 11 | MIT-CMU | PNG/JPEG/TIFF/WebP I/O, colour-pool images, thumbnails | Standard |
| **OpenEXR** (official bindings) | ≥ 3.3 | BSD-3 | Float EXR output, multi-layer AOVs; EXR HDRI input | HDR pipeline |
| **imageio** + **imageio-ffmpeg** | ≥ 2.36 / ≥ 0.5 | BSD-2 (ffmpeg binary: LGPL build) | MP4/WebM/GIF animation export; Radiance `.hdr` input | Video export without making users install ffmpeg |
| **Open Image Denoise** (bundled shared libraries, bound with `ctypes`) | 2.x | Apache-2.0 | Denoising with albedo/normal AOVs | Photoreal results at low spp. Shipped inside the Structura wheel for all platforms ([20](20-risks.md) R7). |
| **Jinja2** | ≥ 3.1 | BSD-3 | Modern exporters (POV-Ray 3.8 SDL, Sunflow `.sc`, Mitsuba 3 XML), Blender script generation | Declarative text templates instead of string concatenation |
| **platformdirs** | ≥ 4 | MIT | Config, cache and data directories | Cross-platform correctness |
| **tomli-w** | ≥ 1.0 | MIT | Writing themes and presets (reading uses stdlib `tomllib`) | Human-editable config |
| **psutil** | ≥ 6 | BSD-3 | Memory guard (warns before a build exhausts RAM), CPU topology for thread counts | Protects users from out-of-memory crashes |

### 2.1 Bundled assets

| Asset | Licence | Use |
|-------|---------|-----|
| Inter (UI font) | OFL-1.1 | Default UI typeface |
| JetBrains Mono (editor font) | OFL-1.1 | Default code font (ligatures off by default) |
| Lucide icons (SVG) | ISC | Toolbar and panel icons, recoloured per theme at runtime |
| 4–6 small HDRIs from Poly Haven | CC0 | Built-in environment presets (≤ 2K, EXR) |
| Legacy `.rendertemplate` files | LGPL/GPL (from Structure Synth; shipped unmodified as separate data) | Backward-compatible template export |
| Structure Synth example scripts | LGPL/GPL (shipped as separate data, `resources/legacy/`) | Examples gallery and golden corpus |
| StructureSynth-code-samples | MIT | Examples gallery and golden corpus |

## 3. Development dependencies (not shipped)

| Tool | Purpose |
|------|---------|
| ruff | Lint and format, including complexity and size rules ([17](17-code-standards-and-layout.md)) |
| mypy (`--strict`) | Static typing gate |
| import-linter | Layer contracts ([02](02-architecture.md) §4) |
| pytest, pytest-qt, pytest-xdist, pytest-benchmark, hypothesis | Tests ([18](18-testing-and-quality.md)) |
| scikit-image | SSIM/PSNR in render regression tests |
| pre-commit | Local gates |
| Mesa llvmpipe via EGL (CI only) | Software OpenGL 4.5, so the GLSL preview and the wgpu-GL backend run in headless CI |
| pocl (runtime dep, used by CI) | OpenCL kernels execute on the CPU in CI |
| Qt5 + C++ toolchain (golden generator only) | Builds the original Structure Synth model code to produce golden outputs ([18](18-testing-and-quality.md) §3) |

## 4. Alternatives considered (summary; details in ADRs)

| Need | Chosen | Rejected alternatives | ADR |
|------|--------|----------------------|-----|
| GPU APIs | OpenGL/GLSL (preview) + CUDA, OpenCL, WGSL (precision) | wgpu-only (did not meet the owner's CUDA/OpenCL/GLSL requirement); Vulkan via `vulkan` (too low level); Qt RHI (no Python compute API); OptiX (NVIDIA-only; the GTX 1660 has no RT cores); Taichi (maintenance risk) | [0013](adr/0013-two-render-engines.md) |
| CPU fallback | Numba | Cython (build complexity, no single-source with GPU); pure numpy (no per-ray branching); multiprocessing (IPC cost for large scenes) | [0003](adr/0003-cpu-fallback-numba.md) |
| Single kernel source | SKL (restricted Python) → Numba, CUDA C, OpenCL C, WGSL, GLSL | Hand-written per-API kernels (violates DRY); Slang (immature CPU target from Python) | [0004](adr/0004-single-source-kernels.md) |
| Builder speed | Numba kernel over compiled rule tables | Pure-Python tree walk (≈50× slower); numpy BFS vectorisation (breaks legacy RNG order) | [0005](adr/0005-builder-numba.md) |
| Editor widget | Custom `QPlainTextEdit` stack | QScintilla (no PySide6 bindings); embedding Monaco in QtWebEngine (200 MB, a second UI toolkit, awkward theming) | [0007](adr/0007-editor-widget.md) |
| Theme format | TOML semantic-role themes + VS Code / base16 importers | QSS-only (no syntax roles); per-widget colours (not DRY) | [0008](adr/0008-theme-format.md) |
| USD | usd-core | Hand-written `.usda` (no `.usdc`/`.usdz`, fragile) | [0009](adr/0009-usd-usd-core.md) |

## 5. Version & update policy

- Dependencies are pinned by lock file. wgpu is pinned to an **exact minor version** because its API still
  moves before 1.0.
- Each quarter: a deliberate dependency upgrade PR that runs the full CI matrix, including render regression.
- Security updates (Pillow, OpenEXR, Qt) are applied immediately.
