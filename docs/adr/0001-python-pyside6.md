# ADR-0001: Python 3.12 + PySide6 as the application platform

- Status: Proposed
- Date: planning phase

## Context

The brief mandates Python and PySide6. We still need to fix a baseline Python version and decide which Qt
modules we rely on.

## Decision

- **Python 3.12** baseline; CI also tests 3.13.
- **PySide6 ≥ 6.8**, using QtCore, QtGui, QtWidgets, QtSvg and QtQml (`QJSEngine` for legacy JavaScript).
- Qt Quick/QML UIs are not used. Widgets give mature text editing, docking and native dialogs.
- The Fusion style is used everywhere, with generated QSS, for a consistent look.

## Alternatives considered

- **PyQt6:** functionally similar, but GPL/commercial licensing and not what the brief mandates.
- **Qt Quick/QML UI:** attractive visuals, but its text editing and docking are weaker for an IDE-like tool.
  It would also split UI technology.

## Consequences

- QScintilla is unavailable (it has no PySide6 bindings). See ADR-0007.
- `QJSEngine` provides the legacy `#javascript` support with no extra dependency.
- Domain layers must stay Qt-free, so the CLI and tests do not need a GUI (import-linter contract).
