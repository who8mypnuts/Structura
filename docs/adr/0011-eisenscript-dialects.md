# ADR-0011: v1 compatibility by default, opt-in v2 dialect

- Status: Proposed
- Date: planning phase

## Context

Users have years of `.es` files that depend on exact 1.5 behaviour, including quirks such as
substring-replacing `#define`, HSV quantisation and RNG order. We also want materials, lights, camera,
expressions and fixed defaults.

## Decision

- Every file is **v1 (compat)** unless its first non-blank line is `#version 2`.
- v1 reproduces 1.5 exactly, apart from the documented defect fixes that cannot change valid output (size/v
  aliases, `#include`, triangle tags, DFS-cull hang). Quirks are reproduced and linted.
- v2 is a language-level superset with better defaults.
- `structura convert --to v2` migrates files explicitly, with a diff for review.

## Alternatives considered

- **Only a modern dialect:** breaks the existing corpus.
- **Silent fixes in one dialect:** unpredictable changes to old artworks.

## Consequences

- Two preprocessors, with a shared lexer, parser and compiler gated by dialect flags.
- The golden suite guards v1, and the spec examples guard v2.
