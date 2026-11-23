"""Curated knot library (KNOTS_TAB_PLAN Phase 0): the loader of the curated knot catalogue."""

from __future__ import annotations

from structura.core.scene.knot_library import KnotComponent, knots


def test_library_loads_the_curated_knots() -> None:
    """Phase 0 ships the first curated knots and the catalogue format is fixed."""
    assert set(knots()) == {"trefoil", "unknot"}


def test_trefoil_is_a_closed_torus_knot() -> None:
    (component,) = knots()["trefoil"].components
    assert isinstance(component, KnotComponent)
    assert component.closed
    assert len(component.beads) >= 3  # long enough to tessellate a smooth tube
    assert component.radius > 0.0
    assert len(component.rgba) == 4


def test_unknot_is_one_closed_loop() -> None:
    (component,) = knots()["unknot"].components
    assert isinstance(component, KnotComponent)
    assert component.closed
    assert len(component.beads) >= 3
    assert component.radius > 0.0
    assert len(component.rgba) == 4


def test_knot_library_is_loaded_once_per_process() -> None:
    assert knots() is knots()
