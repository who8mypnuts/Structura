"""Enforce the size limits from docs/17-code-standards-and-layout.md §1.

Counts *code lines* (non-blank, non-comment, excluding docstrings) per module, class and function, and the
control-flow nesting depth inside functions. Exit status 1 if any hard limit is exceeded.

Exemptions: a ``# size-exempt: <reason>`` comment on the ``def``/``class`` line, or anywhere in the first
five lines of a module for module-level limits.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

HARD_MODULE = 400
HARD_FUNCTION = 50
HARD_CLASS = 300
HARD_NESTING = 4
ROOTS = ("src", "tools", "tests")
SKIP_PARTS = {"golden", "__pycache__", ".venv", "_generated", "resources"}
NEST_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try, ast.Match)
EXEMPT = "size-exempt:"


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    what: str
    value: int
    limit: int

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.what} = {self.value} (limit {self.limit})"


def docstring_lines(tree: ast.AST) -> set[int]:
    """Line numbers occupied by docstrings (they don't count as code)."""
    lines: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            lines.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return lines


def code_line_set(source_lines: list[str], skip: set[int]) -> set[int]:
    """1-based line numbers that hold code."""
    result: set[int] = set()
    for i, text in enumerate(source_lines, start=1):
        stripped = text.strip()
        if stripped and not stripped.startswith("#") and i not in skip:
            result.add(i)
    return result


def count_in(code: set[int], start: int, end: int) -> int:
    return sum(1 for i in range(start, end + 1) if i in code)


def _is_elif(parent: ast.AST, child: ast.AST) -> bool:
    return isinstance(parent, ast.If) and isinstance(child, ast.If) and parent.orelse == [child]


def nesting_depth(node: ast.AST, depth: int = 0) -> int:
    """Maximum nesting of control-flow statements below ``node``.

    Nested defs are measured separately, and an ``elif`` counts at the level of its ``if``.
    """
    best = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        nested = isinstance(child, NEST_NODES) and not _is_elif(node, child)
        best = max(best, nesting_depth(child, depth + 1 if nested else depth))
    return best


def check_file(path: Path) -> list[Violation]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    tree = ast.parse(text, filename=str(path))
    code = code_line_set(lines, docstring_lines(tree))
    found: list[Violation] = []
    module_exempt = any(EXEMPT in line for line in lines[:5])
    if not module_exempt and len(code) > HARD_MODULE:
        found.append(Violation(path, 1, "module code lines", len(code), HARD_MODULE))
    for node in ast.walk(tree):
        found.extend(check_node(path, node, lines, code))
    return found


def check_node(path: Path, node: ast.AST, lines: list[str], code: set[int]) -> list[Violation]:
    if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return []
    if EXEMPT in lines[node.lineno - 1]:
        return []
    size = count_in(code, node.lineno, node.end_lineno or node.lineno)
    if isinstance(node, ast.ClassDef):
        return (
            [Violation(path, node.lineno, f"class {node.name} code lines", size, HARD_CLASS)]
            if size > HARD_CLASS
            else []
        )
    found = []
    if size > HARD_FUNCTION:
        found.append(Violation(path, node.lineno, f"function {node.name} code lines", size, HARD_FUNCTION))
    depth = nesting_depth(node)
    if depth > HARD_NESTING:
        found.append(Violation(path, node.lineno, f"function {node.name} nesting", depth, HARD_NESTING))
    return found


def iter_python_files(root: Path) -> list[Path]:
    files = []
    for base in ROOTS:
        for path in sorted((root / base).rglob("*.py")):
            if not SKIP_PARTS.intersection(path.parts):
                files.append(path)
    return files


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    violations = [v for f in iter_python_files(root) for v in check_file(f)]
    for violation in violations:
        print(violation)
    print(f"check_sizes: {len(violations)} violation(s)")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
