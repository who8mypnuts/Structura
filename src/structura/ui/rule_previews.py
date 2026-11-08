"""Structure previews on hover (docs/12 §2.3, P2): hovering a rule name shows a thumbnail of that rule built
on its own. The rule-alone script (core.lang.restructure.rule_alone) is built and rendered by the 'preview'
integrator on the compute lane; images are cached on disk by the script's hash, so each is made once."""

from __future__ import annotations

import hashlib
from pathlib import Path

import platformdirs
from PIL import Image
from PySide6.QtCore import QObject, Signal, Slot

from ..core.lang.restructure import rule_alone
from ..render.thumbnail import script_thumbnail
from ..services.jobs import FunctionJob, JobContext, JobRunner, Lane

SIZE = (192, 144)


def cache_dir() -> Path:
    return Path(platformdirs.user_cache_dir("structura")) / "thumbnails" / "rules"


class RulePreviews(QObject):
    ready = Signal(str)  # the rule whose preview was just made

    def __init__(self, runner: JobRunner, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.runner = runner
        self.pending: dict[Path, str] = {}  # image being made → its rule
        self.failed: set[Path] = set()  # rules that do not build on their own

    def image(self, text: str, rule: str, seed: int = 0) -> Path | None:
        """The cached preview of ``rule`` in ``text``; None while it is being made (``ready`` follows) or
        when the rule cannot be built alone."""
        alone = rule_alone(text, rule)
        if alone is None:
            return None
        path = cache_dir() / (hashlib.sha1(f"{seed}\n{alone}".encode()).hexdigest()[:20] + ".png")
        if path.exists():
            return path
        if path not in self.pending and path not in self.failed:
            self.pending[path] = rule
            job = FunctionJob(f"rule preview {rule}", Lane.COMPUTE, _make(alone, seed, path))
            self.runner.submit(job).finished.connect(self._done)  # a bound slot: runs on the GUI thread
        return None

    @Slot(object)
    def _done(self, result: object) -> None:
        if not isinstance(result, tuple):
            return
        path, made = result
        rule = self.pending.pop(path, "")
        if made:
            self.ready.emit(rule)
        else:
            self.failed.add(path)


def _make(script: str, seed: int, path: Path):  # type: ignore[no-untyped-def]
    def run(ctx: JobContext) -> tuple[Path, bool]:
        try:
            rgb, _ = script_thumbnail(script, SIZE, seed)
        except Exception:  # a rule that does not build on its own shows no picture
            return path, False
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgb).save(path)
        return path, True

    return run
