# 20 — Risk Register

Likelihood (L) and Impact (I) are rated 1–5. Exposure = L × I. Risks with exposure ≥ 12 are reviewed
every two weeks. The rest are reviewed at each phase gate.

| ID | Risk | L | I | Exp. | Mitigation | Trigger / owner |
|----|------|---|---|------|------------|-----------------|
| R1 | **SKL transpiler is harder than expected** (type inference, performance parity) | 3 | 5 | 15 | Spike S1 first, with hard exit criteria; a defined fallback (dual kernels + parity suite) that keeps the schedule ([11](11-compute-backends.md) §9) | S1 misses exit criteria / Rendering lead |
| R2 | **wgpu-py API churn** before its 1.0 | 4 | 3 | 12 | Exact minor pin; all wgpu usage isolated in `structura.gpu` (small surface); quarterly upgrade PRs with full CI | Upgrade PR fails / Rendering lead |
| R3 | **Five code-generation targets** (Numba, CUDA, OpenCL, WGSL, GLSL) multiply edge cases | 3 | 4 | 12 | Shared `CLikeEmitter`; flat buffer ABI; per-target probe-kernel parity in CI (pocl, llvmpipe, NVRTC compile); nightly real-GPU runs | Parity failures / Rendering |
| R4 | **GPU watchdog timeouts** (Windows TDR ≈ 2 s) on heavy scenes | 3 | 4 | 12 | Dispatch budgeting ≤ 50 ms, adaptive tile and spp sizing from timestamp queries ([04](04-concurrency-model.md) §5); device-lost recovery → CPU | Device-lost telemetry in beta / Rendering lead |
| R5 | **Numba JIT latency or cache problems** (first-run stalls, stale caches, arm64 quirks) | 3 | 3 | 9 | `cache=True`; installer warm-up; background warm-up Job; CI on macOS arm64; cache versioned by Structura version | Cold start > 2.5 s / Engine lead |
| R6 | **Numba threading-layer re-entrancy** crashes when parallel kernels run concurrently | 2 | 5 | 10 | A single compute lane for `parallel=True` kernels, enforced by a runtime assertion in debug builds ([04](04-concurrency-model.md) §6) | Any crash in parallel kernels / Engine lead |
| R7 | **OIDN binary redistribution** (size, ABI, platform coverage) | 2 | 3 | 6 | Pin an OIDN 2.x release; ship its CPU libs in the wheel per platform; ctypes smoke test at start-up; verify the Apache-2.0 notices | Wheel > size budget or load failure / Pipeline lead |
| R8 | **Golden generator fidelity** (Qt5 vs the Qt4 used by 1.5; compiler float differences) | 3 | 4 | 12 | Cross-check a sample against the released 1.5 binary; tolerance rules ([18](18-testing-and-quality.md) §3.3); divergence reports | Unexplained golden diffs / Engine lead |
| R9 | **GIL-induced UI stutter** from Python work on worker threads or third-party calls | 3 | 4 | 12 | UI-stall watchdog in CI; heavy loops in Numba/numpy; chunked third-party calls; an isolated subprocess lane if needed ([04](04-concurrency-model.md) §8) | Watchdog failures / App lead |
| R10 | **Memory exhaustion** with huge builds (pending states, GPU buffers) | 3 | 4 | 12 | Memory guard (psutil); float32 IR; streaming chunks; GPU paging; CPU render fallback above the VRAM threshold | OOM reports / Engine lead |
| R11 | **Licensing.** Structura is **MIT**, but Structure Synth is LGPL-2.1/GPL-3, so its code must not be translated. POV-Ray is AGPL-3. Theme palettes, NVRTC redistribution, usd-core, ffmpeg and OIDN need notices. | 3 | 5 | 15 | Clean re-implementation from the behavioural spec (ADR-0010); legacy templates/examples shipped unmodified as separately licensed data; community samples are MIT (owner-confirmed); `THIRD_PARTY_NOTICES.md` maintained; legal review before the first public build | Before first public build / Project lead |
| R12 | **DCC interoperability variance** (PointInstancer primvars, EXT_mesh_gpu_instancing support differ across Blender, Houdini, Omniverse, engines) | 4 | 3 | 12 | Safe defaults (glTF baked; USD instanced with a baked option); a compatibility matrix test plan; nightly Blender checks; clear UI hints | Compatibility issues in beta / Pipeline lead |
| R13 | **Scope creep** (editor and renderer are open-ended) | 4 | 3 | 12 | P0/P1/P2 tiers; a feature freeze at phase H start; new features need an ADR or roadmap change | Phase slips > 2 weeks / Project lead |
| R14 | **GPU/CPU parity drift** from FMA and fast-math differences | 3 | 3 | 9 | `@func(exact=True)` for geometry; ULP and statistical tolerances; per-backend references ([11](11-compute-backends.md) §8) | Flaky parity tests / Rendering lead |
| R15 | **Reference GPU headroom:** the GTX 1660 has 6 GiB VRAM and no RT cores; the preview and precision engines share it | 3 | 3 | 9 | VRAM budgeting (preview ≤ 400 MiB at 5M instances); device-lane duty-cycle cap; paging; CPU fallback above 80% VRAM | VRAM warnings / Rendering |
| R16 | **Packaging/notarisation** with LLVM (Numba), wgpu-native and OIDN binaries | 3 | 4 | 12 | Packaging smoke test from Phase F; signed builds in CI from Phase U1 | Installer failures / Pipeline lead |
| R17 | **Python version transitions** (3.13/3.14, free-threading), with wheels lagging | 2 | 3 | 6 | 3.12 baseline; 3.13 in CI; a dependency wheel-availability check job | Missing wheels / Pipeline lead |
| R18 | **No GPU in the agent sandbox:** CUDA is compile-only and performance is unmeasured | 4 | 3 | 12 | NVRTC compile checks; pocl and llvmpipe execution for every other target; owner runs `tools/bench` and `pytest -m gpu` at M2/M6 checkpoints | Owner checkpoint results / Agent |
| R19 | **Security.** Templates (`runAfter`), JS `Builder.execute`, and Python scripts can run commands | 3 | 4 | 12 | Explicit confirmation per command (remembered per file hash); never auto-run on open; scripts from untrusted sources are flagged; docs explain the risks | — / App lead |
| R20 | **Legacy corner cases** (float32 thresholds in `minsize`/`maxsize`, QColor rounding) cause object-set differences | 3 | 3 | 9 | Compat mode uses float32 and C++ accumulation order; a documented-deviations list ([01](01-legacy-analysis.md) §1.4); per-script tolerances only with an explicit justification | Golden failures / Engine lead |

## Assumptions to confirm at kick-off

1. Structura's licence: **MIT** (ADR-0010) — *confirmed*.
2. Reference hardware: **NVIDIA GTX 1660, 6 GiB** — *confirmed*.
3. Minimum OS versions: Windows 10 22H2+, macOS 12+, Linux with Vulkan 1.1 or a GL fallback via wgpu.
4. Agent-driven execution with owner checkpoints (ADR-0014) — *confirmed*.
5. Community sample scripts are MIT — *confirmed*.
