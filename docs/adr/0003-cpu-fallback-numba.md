# ADR-0003: Numba for the multithreaded CPU fallback

- Status: Proposed
- Date: planning phase

## Context

A multithreaded CPU path is essential: for machines without a usable GPU, for scenes that exceed GPU limits,
and for headless servers. The GUI must stay responsive while it runs.

## Decision

Use **Numba** (`@njit(nogil=True, parallel=True, cache=True)`) for CPU kernels: the builder, BVH build, CPU
renderer, and tessellation hot loops. Parallel kernels run only on the single compute lane
([04](../04-concurrency-model.md) §6).

## Alternatives considered

- **Cython / C++ extension:** faster in corner cases, but adds compiled-extension build complexity per
  platform and cannot share source with the GPU path.
- **numpy only:** cannot express per-ray branching traversal efficiently.
- **multiprocessing:** serialisation or shared-memory overhead for large scenes; complex cancellation.

## Consequences

- JIT warm-up must be managed (installer warm-up, cache, background Job).
- Numba's `workqueue` threading layer is not re-entrant, hence the single-lane rule.
- The same generated code can run with `NUMBA_DISABLE_JIT=1` for debugging.
