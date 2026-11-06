# ADR-0014: Agent-driven execution model

- Status: **Accepted** (project owner: "You'll be working on this, so it will be much faster")

## Context

The original roadmap assumed a 4-engineer team and 44 weeks. The project owner has assigned implementation to
an AI engineering agent. The agent works in a Linux sandbox without a GPU: Numba, pocl, NVRTC and llvmpipe are
available. The owner has the reference GTX 1660 and desktop operating systems.

## Decision

- Replace person-week phases with **dependency-ordered milestones M0–M9** ([19](../19-roadmap.md)), each with
  a test-verified checkpoint.
- Keep a living **[PROGRESS.md](../PROGRESS.md)** log: what was built, how it was verified, what is next, and
  what needs the owner's hardware.
- Everything the sandbox can verify is verified there: unit, golden, parity on Numba/pocl/llvmpipe, and
  NVRTC compile checks. Hardware-only verification is packaged as scripts the owner runs (`tools/bench`,
  `pytest -m gpu`).

## Consequences

- Performance numbers measured in the sandbox are indicative only. Budgets are confirmed on the GTX 1660.
- The quality gates (sizes, typing, layering, tests) matter even more, because they are the main guard against
  drift in a large, fast-moving codebase.
