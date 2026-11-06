# ADR-0013: Two render engines — GLSL/Numba preview, multi-backend precision renderer

- Status: **Accepted** (project owner requirement)
- Supersedes: ADR-0002, ADR-0012

## Context

The project owner asked for:

1. a **lower-precision preview engine** using GLSL, with a Numba fallback;
2. a **precise engine** that can use **OpenCL, CUDA** and other GPU APIs, **WGSL**, and a **CPU fallback**.

The reference GPU is an **NVIDIA GTX 1660 (6 GiB)**: Turing, compute capability 7.5, no RT cores.

## Decision

| | Structura Preview | Structura Render |
|---|-------------------|------------------|
| Role | Interactive viewport, picking, thumbnails, variation grids | Final physically based images; progressive "render in viewport" |
| GPU API | OpenGL 3.3 core (4.1 on macOS), GLSL, `QOpenGLWidget` + ModernGL | CUDA (cuda-python + NVRTC), OpenCL (pyopencl), WGSL (wgpu, offscreen compute) |
| CPU | Numba ray-cast with the `preview` integrator | Numba, same kernels |
| Precision | fp32 transforms, unorm8 colours, screen-space effects, half-res AO | fp32 kernels, robust offsets, compensated accumulation, `exact` geometry functions |
| Thread | GUI thread (GL context affinity), budgeted ticks | Dedicated **device lane** (QThread owning the compute context) |
| Code source | Hand-written raster GLSL + SKL-emitted shared modules | SKL for every kernel ([11](../11-compute-backends.md)) |

- Auto backend priority: CUDA → OpenCL GPU → wgpu → Numba.
- Every backend runs the same SKL kernels, so features are identical everywhere.

## Alternatives considered

- **wgpu for everything** (ADR-0002): one API, but it doesn't meet the explicit CUDA/OpenCL/GLSL
  requirement. Embedding a wgpu surface in Qt was also the riskiest spike (S6).
- **Separate hand-written kernels per API:** violates DRY. SKL keeps one source.
- **OptiX / hardware RT:** the reference GPU has no RT cores, and it is NVIDIA-only.

## Consequences

- `QOpenGLWidget` is the most mature GL embedding in Qt, so spike S6 is retired.
- There are five code-generation targets, but they share a `CLikeEmitter` base. The test matrix gains pocl
  (OpenCL on CPU) and NVRTC compile checks in CI.
- New required dependencies: `moderngl`, `pyopencl` + `pocl-binary-distribution`, `cuda-python` +
  `nvidia-cuda-nvrtc-cu12` (Windows/Linux only; CUDA does not exist on macOS), alongside `wgpu` and `numba`.
