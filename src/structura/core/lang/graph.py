"""The rule call graph of a parsed script (docs/06 §6): who calls whom, what the top level reaches, and
which rules recurse. Only user rules are nodes; primitives, tags and triangles are leaves and left out."""

from __future__ import annotations

from collections.abc import Iterator

from .ast import CallAction, Program

TOP = "<top>"
Graph = dict[str, set[str]]


def call_graph(program: Program) -> Graph:
    """Rule name → the user rules it calls (calls and maxdepth retirements). ``TOP`` is the top level."""
    rules = {r.name for r in program.rules}
    graph: Graph = {TOP: set()}
    for name, body in [(TOP, program.top), *((r.name, r.body) for r in program.rules)]:
        targets = graph.setdefault(name, set())
        targets.update(a.target for a in body if isinstance(a, CallAction) and a.target in rules)
    for rule in program.rules:
        if rule.retirement in rules:
            graph[rule.name].add(rule.retirement)
    return graph


def reachable(graph: Graph, start: str = TOP) -> set[str]:
    seen, stack = {start}, [start]
    while stack:
        for target in graph.get(stack.pop(), ()):
            if target not in seen:
                seen.add(target)
                stack.append(target)
    return seen - {TOP}


class _Components:
    """Tarjan's strongly connected components, iterative (deep scripts must not hit the recursion limit)."""

    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self.index: dict[str, int] = {}
        self.low: dict[str, int] = {}
        self.stack: list[str] = []
        self.on_stack: set[str] = set()
        self.groups: list[frozenset[str]] = []

    def _enter(self, node: str) -> Iterator[str]:
        self.index[node] = self.low[node] = len(self.index)
        self.stack.append(node)
        self.on_stack.add(node)
        return iter(sorted(self.graph.get(node, ())))

    def visit(self, root: str) -> None:
        work = [(root, self._enter(root))]
        while work:
            node, children = work[-1]
            child = next(children, None)
            if child is None:
                work.pop()
                if work:
                    parent = work[-1][0]
                    self.low[parent] = min(self.low[parent], self.low[node])
                self._close(node)
            elif child not in self.index:
                work.append((child, self._enter(child)))
            elif child in self.on_stack:
                self.low[node] = min(self.low[node], self.index[child])

    def _close(self, node: str) -> None:
        if self.low[node] != self.index[node]:
            return
        members: set[str] = set()
        while not members or node not in members:
            member = self.stack.pop()
            self.on_stack.discard(member)
            members.add(member)
        if len(members) > 1 or node in self.graph.get(node, ()):
            self.groups.append(frozenset(members))


def recursive_groups(graph: Graph) -> list[frozenset[str]]:
    """Strongly connected components that contain a cycle (including a rule that calls itself)."""
    components = _Components(graph)
    for root in graph:
        if root not in components.index:
            components.visit(root)
    return components.groups
