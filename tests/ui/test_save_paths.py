"""Save dialogs suggest the open script's folder, not the current working directory (docs/14 §9)."""

from __future__ import annotations

from pathlib import Path

from structura.ui.save_paths import documents_folder, suggested_path


def test_a_script_s_folder_wins_over_the_documents_fallback() -> None:
    script = Path("/projects/towers/spire.es")
    assert suggested_path(script, "spire.usdc") == "/projects/towers/spire.usdc"


def test_no_script_falls_back_to_the_documents_folder() -> None:
    suggested = Path(suggested_path(None, "render.png"))
    assert suggested.parent == documents_folder() and suggested.name == "render.png"
