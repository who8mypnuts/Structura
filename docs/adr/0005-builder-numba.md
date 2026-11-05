# ADR-0005: Numba-compiled, resumable builder over flat rule tables

- Status: Proposed (pending spike S4)
- Date: planning phase

## Context

Structure Synth's builder walks C++ objects. A straightforward Python port would run tens of times slower,
and live coding needs about 1M primitives in under a second. Compatibility also requires the *exact* RNG
draw order, which rules out naive vectorisation of breadth-first generations.

## Decision

Compile the rule set into flat numpy tables (`RuleProgram`). Expand it in a **Numba kernel that is
resumable in time slices**. The slices give progress, cancellation and streaming without Python callbacks
inside Numba. MT19937 is implemented in Numba and verified against numpy's `RandomState` stream.

## Alternatives considered

- **Pure-Python tree walk:** too slow.
- **numpy-vectorised BFS:** fast, but breaks sequential RNG order and so compatibility.
- **C++ extension port of Builder.cpp:** fast, but adds a native build and duplicates logic outside the
  Python codebase.

## Consequences

- Per-state storage must be fixed-layout (depth vectors sized by the number of depth-limited rules).
- Full ancestry is reconstructed by deterministic re-runs (trace mode), not stored.
