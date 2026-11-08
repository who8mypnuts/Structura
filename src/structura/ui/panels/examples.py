"""Examples panel (docs/14 §3): a gallery of the bundled legacy and community scripts with thumbnails, a group
filter and search. Double-click opens a copy (the bundled files stay untouched).

Thumbnails are rendered once by the 'preview' integrator (render/thumbnail.py), one short compute-lane job
at a time so other work interleaves, and cached on disk by script content. Cached ones are read on the io
lane. With STRUCTURA_PREVIEW=off or STRUCTURA_THUMBNAILS=off (tests, headless use) no thumbnails are made.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import numpy as np
import platformdirs
from PIL import Image
from PySide6.QtCore import QObject, QSize, Qt, Signal, Slot
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap, QShowEvent
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from ... import __version__
from ...render.thumbnail import script_thumbnail
from ...services.jobs import FunctionJob, JobContext, JobRunner, Lane
from ..i18n import tr

RESOURCES = Path(__file__).resolve().parents[2] / "resources"
SOURCES = (  # (group, folder, sub-folders become their own groups)
    ("Classic", RESOURCES / "legacy" / "examples", True),
    ("Community", RESOURCES / "examples" / "community", False),
)
TILE = (104, 78)  # two columns fit the side bar
CACHE = Path(platformdirs.user_cache_dir("structura")) / "thumbnails"
ALL = "All"


def example_files() -> list[tuple[str, Path]]:
    found = []
    for group, root, nested in SOURCES:
        for path in sorted(root.rglob("*.es"), key=lambda p: p.stem.lower()):
            rel = path.relative_to(root)
            found.append((f"{group} · {rel.parts[0]}" if nested and len(rel.parts) > 1 else group, path))
    return found


def cache_file(path: Path) -> Path:
    digest = hashlib.sha1(path.read_bytes() + f"|{__version__}|{TILE}".encode()).hexdigest()
    return CACHE / f"{digest}.png"


def _qimage(rgb: np.ndarray) -> QImage:
    rgb = np.ascontiguousarray(rgb)
    h, w, _ = rgb.shape
    return QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()


def _load_cached(paths: list[Path]) -> Any:
    def run(ctx: JobContext) -> tuple[dict[Path, np.ndarray], list[Path]]:
        cached, missing = {}, []
        for path in paths:
            file = cache_file(path)
            if file.exists():
                cached[path] = np.asarray(Image.open(file).convert("RGB"))
            else:
                missing.append(path)
        return cached, missing

    return run


def _render(path: Path) -> Any:
    def run(ctx: JobContext) -> tuple[Path, np.ndarray]:
        try:
            rgb, _ = script_thumbnail(path.read_text(encoding="utf-8", errors="replace"), TILE)
        except Exception:  # a script that does not build still gets a (blank) tile
            rgb = np.zeros((TILE[1], TILE[0], 3), np.uint8)
        CACHE.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgb).save(cache_file(path))
        return path, rgb

    return run


class Thumbnails(QObject):
    """Loads cached thumbnails, then renders the missing ones one job at a time."""

    ready = Signal(object, object)  # Path, QImage

    def __init__(self, runner: JobRunner, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.runner = runner
        self.missing: list[Path] = []
        self.started = False

    def start(self, paths: list[Path]) -> None:
        off = os.environ.get("STRUCTURA_PREVIEW", "auto").lower() == "off"
        if self.started or off or os.environ.get("STRUCTURA_THUMBNAILS", "on").lower() == "off":
            return
        self.started = True
        self.runner.submit(FunctionJob("example thumbnails (cached)", Lane.IO, _load_cached(paths))).finished.connect(
            self._cached
        )

    @Slot(object)
    def _cached(self, result: tuple[dict[Path, np.ndarray], list[Path]]) -> None:
        cached, self.missing = result
        for path, rgb in cached.items():
            self.ready.emit(path, _qimage(rgb))
        self._next()

    def _next(self) -> None:
        if self.missing:
            path = self.missing.pop(0)
            job = FunctionJob(f"example thumbnail {path.stem}", Lane.COMPUTE, _render(path))
            self.runner.submit(job).finished.connect(self._rendered)

    @Slot(object)
    def _rendered(self, result: tuple[Path, np.ndarray]) -> None:
        path, rgb = result
        self.ready.emit(path, _qimage(rgb))
        self._next()


class ExamplesPanel(QWidget):
    open_example = Signal(Path)

    def __init__(self, runner: JobRunner | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.search = QLineEdit()
        self.search.setAccessibleName(tr("Search examples"))
        self.search.setPlaceholderText(tr("Search examples"))
        self.group = QComboBox()
        self.group.setAccessibleName(tr("Example group"))
        self.gallery = QListWidget()
        self.gallery.setAccessibleName(tr("Examples"))
        self.gallery.setViewMode(QListWidget.ViewMode.IconMode)
        self.gallery.setIconSize(QSize(*TILE))
        self.gallery.setGridSize(QSize(TILE[0] + 12, TILE[1] + 32))
        self.gallery.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.gallery.setMovement(QListWidget.Movement.Static)
        self.gallery.setWordWrap(True)
        self.gallery.setUniformItemSizes(True)
        top = QHBoxLayout()
        top.addWidget(self.search, 1)
        top.addWidget(self.group)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(top)
        layout.addWidget(self.gallery, 1)
        self.items: dict[Path, QListWidgetItem] = {}
        self._fill()
        self.search.textChanged.connect(self._filter)
        self.group.currentTextChanged.connect(self._filter)
        self.gallery.itemActivated.connect(self._activate)
        self.gallery.itemDoubleClicked.connect(self._activate)
        self.thumbnails = Thumbnails(runner, self) if runner is not None else None
        if self.thumbnails is not None:
            self.thumbnails.ready.connect(self._thumbnail)

    def _fill(self) -> None:
        placeholder = QPixmap(*TILE)
        placeholder.fill(QColor(128, 128, 128, 60))
        groups: list[str] = []
        for group, path in example_files():
            item = QListWidgetItem(QIcon(placeholder), path.stem)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setData(Qt.ItemDataRole.UserRole + 1, group)
            item.setToolTip(f"{path.stem}\n{group}")
            self.gallery.addItem(item)
            self.items[path] = item
            groups += [group] if group not in groups else []
        self.group.addItems([tr(ALL), *groups])

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        if self.thumbnails is not None:
            self.thumbnails.start(list(self.items))

    @Slot(object, object)
    def _thumbnail(self, path: Path, image: QImage) -> None:
        item = self.items.get(path)
        if item is not None:
            item.setIcon(QIcon(QPixmap.fromImage(image)))

    def _filter(self) -> None:
        needle, group = self.search.text().lower(), self.group.currentText()
        for index in range(self.gallery.count()):
            item = self.gallery.item(index)
            in_group = group == tr(ALL) or item.data(Qt.ItemDataRole.UserRole + 1) == group
            item.setHidden(not in_group or (bool(needle) and needle not in item.text().lower()))

    def visible_names(self) -> list[str]:
        return [self.gallery.item(i).text() for i in range(self.gallery.count()) if not self.gallery.item(i).isHidden()]

    def _activate(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.open_example.emit(Path(path))
