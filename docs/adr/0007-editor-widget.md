# ADR-0007: Custom editor on QPlainTextEdit

- Status: Proposed
- Date: planning phase

## Context

We need a modern code editor: highlighting, completion, diagnostics, multi-cursor, minimap, folding and
inline widgets, all inside a PySide6 application.

## Decision

Build a composed editor on **`QPlainTextEdit`** + `QSyntaxHighlighter`, with small focused components (gutter,
completion popup, hover, multi-cursor, minimap, scrubber). The components are driven by an in-process
language service that reuses the real lexer and parser ([12](../12-editor.md)).

## Alternatives considered

- **QScintilla:** mature, but has no PySide6 bindings.
- **Monaco in QtWebEngine:** excellent editor, but about 200 MB of Chromium, a second UI toolkit and theming
  system, and a JS↔Python bridge for every feature.
- **Third-party Python editor widgets:** none are maintained for PySide6 with the feature set we need.

## Consequences

- Multi-cursor, minimap and sticky scroll must be implemented ourselves (they are scheduled P1).
- Full control over generative-art features (scrubbing, provenance, inline sliders) and app-wide theming.
