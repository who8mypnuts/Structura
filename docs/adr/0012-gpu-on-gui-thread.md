# ADR-0012: All wgpu calls on the GUI thread via a cooperative scheduler

- Status: Proposed (pending spike S6)
- Date: planning phase

## Context

The viewport surface must be presented from the GUI thread. wgpu-py objects are not documented as safe to
share across Python threads. Rendering must still never block the GUI.

## Decision

A **`GpuScheduler`** on the GUI thread interleaves the following each frame, within a CPU budget of about
6 ms ([04](../04-concurrency-model.md) §5):

- viewport frames;
- chunked uploads;
- time-boxed compute dispatches;
- asynchronous readbacks.

Heavy CPU-side preparation (packing, BVH) happens in compute-lane Jobs.

## Alternatives considered

- **A dedicated GPU thread owning the device:** cleaner isolation, but unclear thread-safety in the bindings
  and cross-thread surface presentation problems.
- **A separate GPU process:** robust, but large IPC and complexity costs.

## Consequences

- Dispatches must be small (≤ 50 ms GPU time), which also protects against OS GPU watchdogs.
- If profiling shows encoding cost on the GUI thread above budget, revisit with a superseding ADR
  (for example, a GPU thread for compute only).
