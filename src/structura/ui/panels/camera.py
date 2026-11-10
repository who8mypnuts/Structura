"""Camera panel (docs/14 §3): the viewport camera in numbers, its lens (panels/lens_editor.py: focal length,
depth of field, focus, and the advanced lens), standard views, bookmarks (saved views) and "Copy to Script".
It follows the viewport; editing a number moves the viewport."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.scene.camera import STANDARD_VIEWS, Camera
from ...core.scene.vectors import Vec3
from ..i18n import tr
from ..widgets.fields import spin_box
from .lens_editor import LensEditor


class VectorEdit(QWidget):
    """Three number boxes for a vector (x, y, z); ``changed`` when any of them is edited."""

    changed = Signal()

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        """Builds the three boxes.

        Args:
            name: The vector's accessible name ('Position'); the boxes are '<name> x', '<name> y' and '<name> z'.
            parent: The parent widget.
        """
        super().__init__(parent)
        self.spins = [spin_box(-1e6, 1e6, 3, f"{name} {axis}", buttons=False) for axis in "xyz"]
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        for spin in self.spins:
            row.addWidget(spin)
            spin.valueChanged.connect(self.changed)

    def value(self) -> Vec3:
        x, y, z = (s.value() for s in self.spins)
        return (x, y, z)

    def set_value(self, v: Vec3) -> None:
        for spin, c in zip(self.spins, v, strict=True):
            spin.setValue(float(c))


class CameraPanel(QWidget):
    """The viewport camera in numbers, its lens, standard views, saved views, Lock to Script and Copy to Script."""

    camera_edited = Signal(object)  # Camera
    view_requested = Signal(str)  # a STANDARD_VIEWS name
    copy_to_script = Signal()
    bookmark_requested = Signal()  # save the current view
    bookmark_chosen = Signal(object)  # Camera
    bookmark_deleted = Signal(str)
    lock_toggled = Signal(bool)  # Lock to Script
    focus_selection = Signal()  # focus on the object selected in the viewport

    def __init__(self, parent: QWidget | None = None) -> None:
        """Builds the panel; it shows the default camera until the viewport reports its own.

        Args:
            parent: The parent widget.
        """
        super().__init__(parent)
        self.eye, self.target, self.up = VectorEdit(tr("Position")), VectorEdit(tr("Target")), VectorEdit(tr("Up"))
        self.lens = LensEditor()
        self.lens.focus_selection.connect(self.focus_selection)
        form = QFormLayout()
        for label, widget in ((tr("Position"), self.eye), (tr("Target"), self.target), (tr("Up"), self.up)):
            form.addRow(label, widget)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(form)
        layout.addWidget(self.lens)
        layout.addLayout(self._view_buttons())
        copy = QPushButton(tr("Copy to Script"))
        copy.setToolTip(tr("Write this camera into the script (v1: 'set' lines; v2: a camera block)"))
        copy.clicked.connect(self.copy_to_script)
        self.lock = QCheckBox(tr("Lock to script"))
        self.lock.setToolTip(tr("Every build shows the script's own camera (set lines or camera block)"))
        self.lock.toggled.connect(self.lock_toggled)
        row = QHBoxLayout()
        row.addWidget(copy)
        row.addWidget(self.lock)
        layout.addLayout(row)
        layout.addLayout(self._bookmarks(), 1)
        for edit in (self.eye, self.target, self.up):
            edit.changed.connect(self._edited)
        self.lens.changed.connect(self._edited)
        self._base = Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0))

    def set_locked(self, locked: bool) -> None:
        self.lock.blockSignals(True)
        self.lock.setChecked(locked)
        self.lock.blockSignals(False)

    def _view_buttons(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(4)
        titles = {"front": tr("Front"), "back": tr("Back"), "right": tr("Right"), "left": tr("Left"),
                  "top": tr("Top"), "bottom": tr("Bottom"), "iso": tr("Iso")}  # fmt: skip
        for n, name in enumerate(STANDARD_VIEWS):
            button = QPushButton(titles[name])
            button.setToolTip(tr("Frame the structure, seen from this side"))
            button.clicked.connect(lambda _=False, v=name: self.view_requested.emit(v))
            grid.addWidget(button, n // 4, n % 4)
        return grid

    def _bookmarks(self) -> QVBoxLayout:
        self.list = QListWidget()
        self.list.setAccessibleName(tr("Saved views"))
        self.list.itemActivated.connect(self._choose)
        self.list.itemDoubleClicked.connect(self._choose)
        add, delete = QPushButton(tr("Save View…")), QPushButton(tr("Delete"))
        add.clicked.connect(self.bookmark_requested)
        delete.clicked.connect(self._delete)
        buttons = QHBoxLayout()
        buttons.addWidget(add)
        buttons.addWidget(delete)
        box = QVBoxLayout()
        box.addWidget(self.list, 1)
        box.addLayout(buttons)
        return box

    # -- the camera --------------------------------------------------------------------------------------------
    def show_camera(self, camera: Camera) -> None:
        """Follows the viewport's camera without echoing the change back.

        Args:
            camera: The viewport's camera.
        """
        self._base = camera
        widgets = [*self.eye.spins, *self.target.spins, *self.up.spins]
        for w in widgets:
            w.blockSignals(True)
        self.eye.set_value(camera.eye)
        self.target.set_value(camera.target)
        self.up.set_value(camera.up)
        for w in widgets:
            w.blockSignals(False)
        self.lens.show_camera(camera)

    def camera(self) -> Camera:
        """Returns the camera the panel shows: its position, target and up with the lens editor's lens."""
        lensed = self.lens.camera()
        return replace(self._base, eye=self.eye.value(), target=self.target.value(), up=self.up.value(),
                       fov_y_deg=lensed.fov_y_deg, lens=lensed.lens)  # fmt: skip

    def _edited(self) -> None:
        camera = self.camera()
        if camera.eye != camera.target:
            self.camera_edited.emit(camera)

    # -- bookmarks ---------------------------------------------------------------------------------------------
    def set_bookmarks(self, bookmarks: dict[str, Camera]) -> None:
        self.list.clear()
        for name, camera in bookmarks.items():
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, camera)
            self.list.addItem(item)

    def _choose(self, item: QListWidgetItem) -> None:
        self.bookmark_chosen.emit(item.data(Qt.ItemDataRole.UserRole))

    def _delete(self) -> None:
        item = self.list.currentItem()
        if item is not None:
            self.bookmark_deleted.emit(item.text())
