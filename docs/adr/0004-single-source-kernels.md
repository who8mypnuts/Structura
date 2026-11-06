# ADR-0004: SKL — single-source kernels for CUDA, OpenCL, WGSL, GLSL and Numba

- Status: Proposed (pending spike S1)
- Date: planning phase

## Context

DRY is a core principle, but GPU and CPU renderers are normally written twice. Intersection, sampling,
BSDFs and lights are the most error-prone code, and keeping two copies in sync is a known source of drift.

## Decision

Author kernels in **SKL**, a restricted, typed subset of Python ([11](../11-compute-backends.md)). One front
end produces:

- **CUDA C** (via NVRTC);
- **OpenCL C**;
- **WGSL**;
- **GLSL** (shared preview modules);
- **Numba** Python.

All device buffers use a **flat f32/u32 ABI** with generated accessors. Parity tests verify equivalence
across every available backend.

## Alternatives considered

- **Hand-written WGSL + Numba:** simplest to start, but violates DRY in the riskiest code.
- **Slang (slangpy):** strong GPU story, but its CPU target from Python is not mature or uniform across our
  platforms.
- **Taichi / Warp:** see ADR-0002.

## Consequences

- About 2.5k lines of compiler code to own and test.
- Kernel authors work within SKL's restrictions (no recursion, no dynamic allocation).
- **Fallback:** if spike S1 fails its exit criteria, keep the SKL front end for layouts and builtins only,
  write kernels twice, and rely on the parity suite. A superseding ADR would record that.
