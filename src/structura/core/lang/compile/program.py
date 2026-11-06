"""Flatten a resolved rule set into the RuleProgram tables read by the builder kernel (docs/06 §7)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import numpy as np

from ...errors import BuildError
from ...scene.declarations import SceneDeclarations
from ..ast import CallAction, SetAction
from ..resolve import ResolvedRule, RuleKind, RuleSet
from ..source import Span
from .pools import PoolKind
from .setops import SceneEvent, SetOpTable, compile_set
from .transforms import Transform, compose

ARRAY_FIELDS = (
    "rule_kind",
    "rule_weight",
    "rule_maxdepth",
    "rule_retire",
    "rule_act",
    "rule_alt",
    "rule_prim",
    "rule_tag",
    "rule_tri",
    "rule_slot",
    "rule_listed",
    "alts",
    "act_kind",
    "act_target",
    "act_loops",
    "act_setop",
    "loop_reps",
    "loop_xf",
    "xf_m",
    "xf_col",
    "xf_abs",
    "xf_blend",
    "xf_strength",
    "setop_code",
    "setop_i",
    "setop_f",
    "pool_kind",
    "pool_span",
    "pool_hsv",
    "tri_p",
)
KernelTables = NamedTuple("KernelTables", [(name, np.ndarray) for name in ARRAY_FIELDS])  # type: ignore[misc]


@dataclass(frozen=True)
class RuleProgram:
    """Immutable, Numba-friendly tables (see docs/06 §7 for the column meanings)."""

    rule_kind: np.ndarray  # int8[R]   RuleKind
    rule_weight: np.ndarray  # float64[R]
    rule_maxdepth: np.ndarray  # int32[R]  -1 = unlimited
    rule_retire: np.ndarray  # int32[R]  -1 = none
    rule_act: np.ndarray  # int32[R,2] (start, count) into actions
    rule_alt: np.ndarray  # int32[R,2] (start, count) into alts
    rule_prim: np.ndarray  # int8[R]   primitive kind (PRIMITIVE_NAMES index, 8 = triangle)
    rule_tag: np.ndarray  # int32[R]
    rule_tri: np.ndarray  # int32[R]  row in tri_p
    rule_slot: np.ndarray  # int32[R]  depth-map slot (-1 = none)
    rule_listed: np.ndarray  # uint8[R]  1 if the rule is in Structure Synth's rule list (setRulesMaxDepth)
    alts: np.ndarray  # int32[K]
    act_kind: np.ndarray  # int8[A]  0 = call, 1 = set
    act_target: np.ndarray  # int32[A]
    act_loops: np.ndarray  # int32[A,2] (start, count) into loops
    act_setop: np.ndarray  # int32[A]
    loop_reps: np.ndarray  # int32[L]
    loop_xf: np.ndarray  # int32[L]
    xf_m: np.ndarray  # float32[X,16] row-major 4x4
    xf_col: np.ndarray  # float32[X,4]  (dh, ks, kv, ka)
    xf_abs: np.ndarray  # uint8[X]
    xf_blend: np.ndarray  # float32[X,3]
    xf_strength: np.ndarray  # float64[X]
    setop_code: np.ndarray  # int8[S]
    setop_i: np.ndarray  # int64[S]
    setop_f: np.ndarray  # float64[S]
    pool_kind: np.ndarray  # int8[P]
    pool_span: np.ndarray  # int32[P,3] (start, count, width)
    pool_hsv: np.ndarray  # int32[Q,3]
    tri_p: np.ndarray  # float32[T,3,3]
    top: int
    n_slots: int
    depth_first: bool
    tags: tuple[str, ...]
    events: tuple[SceneEvent, ...]
    errors: tuple[str, ...]
    action_spans: tuple[Span, ...]
    rule_names: tuple[str, ...]
    declarations: SceneDeclarations | None = None  # v2 materials, lights, camera, render blocks

    def kernel_tables(self) -> KernelTables:
        """The numeric tables as a namedtuple (the form Numba kernels accept)."""
        return KernelTables(*(np.ascontiguousarray(getattr(self, name)) for name in ARRAY_FIELDS))


class _Builder:
    def __init__(self, rs: RuleSet, script_dir: Path | None) -> None:
        self.rs, self.script_dir = rs, script_dir
        self.sets = SetOpTable()
        self.sets.pools.add(PoolKind.RANDOM_HUE)  # pool 0: the default colour pool
        self.actions: list[tuple[int, int, int, int, int]] = []
        self.spans: list[Span] = []
        self.loops: list[tuple[int, int]] = []
        self.xfs: list[Transform] = []
        self.act_ranges = np.zeros((len(rs.rules), 2), np.int32)

    def compile_rule_actions(self) -> None:
        for r, rule in enumerate(self.rs.rules):
            self.act_ranges[r] = (len(self.actions), len(rule.actions))
            for action in rule.actions:
                self.spans.append(action.span)
                if isinstance(action, SetAction):
                    op = compile_set(self.sets, action.key, action.value, self.script_dir)
                    self.actions.append((1, -1, 0, 0, op))
                else:
                    self.actions.append(self._call(action))

    def _call(self, action: CallAction) -> tuple[int, int, int, int, int]:
        start = len(self.loops)
        for loop in action.loops:
            self.xfs.append(compose(loop.ops))
            self.loops.append((loop.count, len(self.xfs) - 1))
        return (0, self.rs.index(action.target), start, len(action.loops), -1)


def _depth_slots(rs: RuleSet) -> np.ndarray:
    slots = np.full(len(rs.rules), -1, np.int32)
    n = 0
    for i, rule in enumerate(rs.rules):
        limited = rs.depth_first or rule.maxdepth != -1
        if rule.kind is RuleKind.CUSTOM and i != rs.top and limited:
            slots[i], n = n, n + 1
    return slots


def _rule_columns(rs: RuleSet) -> dict[str, np.ndarray]:
    alts: list[int] = []
    alt_ranges = np.zeros((len(rs.rules), 2), np.int32)
    alternatives = {a for rule in rs.rules for a in rule.alternatives}
    triangles = [r.triangle for r in rs.rules if r.kind is RuleKind.TRIANGLE]
    tri_index = iter(range(len(triangles)))
    cols: dict[str, list[float]] = {k: [] for k in ("kind", "weight", "md", "retire", "prim", "tag", "tri", "listed")}
    for i, rule in enumerate(rs.rules):
        alt_ranges[i] = (len(alts), len(rule.alternatives))
        alts.extend(rule.alternatives)
        _append_rule(cols, rs, rule, i in alternatives, next(tri_index) if rule.kind is RuleKind.TRIANGLE else -1)
    return {
        "rule_kind": np.asarray(cols["kind"], np.int8),
        "rule_weight": np.asarray(cols["weight"], np.float64),
        "rule_maxdepth": np.asarray(cols["md"], np.int32),
        "rule_retire": np.asarray(cols["retire"], np.int32),
        "rule_prim": np.asarray(cols["prim"], np.int8),
        "rule_tag": np.asarray(cols["tag"], np.int32),
        "rule_tri": np.asarray(cols["tri"], np.int32),
        "rule_listed": np.asarray(cols["listed"], np.uint8),
        "rule_alt": alt_ranges,
        "alts": np.asarray(alts, np.int32),
        "tri_p": np.asarray(triangles, np.float32).reshape(-1, 3, 3),
    }


def _append_rule(cols: dict[str, list[float]], rs: RuleSet, rule: ResolvedRule, is_alt: bool, tri: int) -> None:
    if rule.retirement is not None and rule.retirement not in rs.by_name:
        raise BuildError(f"Unable to resolve rule: {rule.retirement}")
    cols["kind"].append(int(rule.kind))
    cols["weight"].append(rule.weight)
    cols["md"].append(rule.maxdepth)
    cols["retire"].append(rs.by_name[rule.retirement] if rule.retirement else -1)
    cols["prim"].append(8 if rule.kind is RuleKind.TRIANGLE else rule.primitive)
    cols["tag"].append(rs.tags.index(rule.tag) if rule.tag in rs.tags else 0)
    cols["tri"].append(tri)
    cols["listed"].append(0 if is_alt or "::" in rule.name or rule.kind is RuleKind.TRIANGLE else 1)


def compile_rule_set(rs: RuleSet, script_dir: Path | None = None) -> RuleProgram:
    b = _Builder(rs, script_dir)
    b.compile_rule_actions()
    acts = np.asarray(b.actions, np.int64).reshape(-1, 5)
    xfs = b.xfs
    pools = b.sets.pools
    slots = _depth_slots(rs)
    return RuleProgram(
        **_rule_columns(rs),  # type: ignore[arg-type]
        rule_act=b.act_ranges,
        rule_slot=slots,
        act_kind=acts[:, 0].astype(np.int8),
        act_target=acts[:, 1].astype(np.int32),
        act_loops=acts[:, 2:4].astype(np.int32),
        act_setop=acts[:, 4].astype(np.int32),
        loop_reps=np.asarray([c for c, _ in b.loops], np.int32),
        loop_xf=np.asarray([x for _, x in b.loops], np.int32),
        xf_m=np.asarray([t.matrix for t in xfs], np.float32).reshape(-1, 16),
        xf_col=np.asarray([(t.dh, t.ks, t.kv, t.ka) for t in xfs], np.float32).reshape(-1, 4),
        xf_abs=np.asarray([t.absolute for t in xfs], np.uint8),
        xf_blend=np.asarray([t.blend_hsv for t in xfs], np.float32).reshape(-1, 3),
        xf_strength=np.asarray([t.strength for t in xfs], np.float64),
        setop_code=np.asarray(b.sets.codes, np.int8),
        setop_i=np.asarray(b.sets.ints, np.int64),
        setop_f=np.asarray(b.sets.floats, np.float64),
        pool_kind=np.asarray(pools.kinds, np.int8),
        pool_span=np.asarray(list(zip(pools.starts, pools.counts, pools.widths, strict=True)), np.int32).reshape(-1, 3),
        pool_hsv=pools.hsv_table().astype(np.int32).reshape(-1, 3),
        top=rs.top,
        n_slots=int((slots >= 0).sum()),
        depth_first=rs.depth_first,
        tags=tuple(rs.tags),
        events=tuple(b.sets.events),
        errors=tuple(b.sets.errors),
        action_spans=tuple(b.spans),
        rule_names=tuple(r.name for r in rs.rules),
    )
