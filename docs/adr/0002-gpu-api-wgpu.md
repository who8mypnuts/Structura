# ADR-0002: WebGPU (wgpu-py) as the single GPU API

- Status: Proposed
- Date: planning phase

## Context

GPU acceleration is mandatory for both the viewport (raster) and the renderer (compute). Features must be
identical on Windows, macOS and Linux. macOS OpenGL is frozen at 4.1 (no compute shaders) and deprecated.
CUDA/OptiX are NVIDIA-only.

## Decision

Use **wgpu-py** (WebGPU over Vulkan / Metal / D3D12) for all GPU work. Embed it in Qt via **rendercanvas**.
Write shaders in WGSL; renderer kernels are generated from SKL (ADR-0004). All wgpu usage is isolated in
`structura.gpu`.

## Alternatives considered

| Option | Why not |
|--------|---------|
| ModernGL / OpenGL 4.x | No compute on macOS; deprecated there |
| Vulkan via Python bindings | Very low level; macOS needs MoltenVK setup; large surface |
| Qt RHI | No Python API for compute |
| CUDA, OptiX, NVIDIA Warp, Dr.Jit | NVIDIA-only GPU paths |
| Taichi | Single-source GPU+CPU is attractive, but development activity has slowed, Python-version support lags, and embedding in Qt widgets is weak |
| PyOpenCL | OpenCL is deprecated on macOS; no raster path |

## Consequences

- No hardware ray-tracing cores (WebGPU does not expose them). We rely on compute BVH traversal, which spike
  S2 must validate.
- WGSL lacks float atomics and recursion. The design uses filter importance sampling (no splatting) and
  iterative integrators.
- The API moves before 1.0, so we use an exact version pin and keep the surface small (risk R2).
