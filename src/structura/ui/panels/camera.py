"""Camera panel (docs/14 §3): the viewport camera in numbers, standard views, bookmarks (saved views) and
"Copy to Script". It follows the viewport; editing a number moves the viewport."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.scene.camera import STANDARD_VIEWS, Camera, Vec3
from ..i18n import tr


def _spin(low: float, high: float, decimals: int = 3, name: str = "") -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(low, high)
    spin.setDecimals(decimals)
    spin.setKeyboardTracking(False)  # apply on Enter or focus change, not on every typed digit
    spin.setAccessibleName(name)
    spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
    return spin


class VectorEdit(QWidget):
    changed = Signal()

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spins = [_spin(-1e6, 1e6, name=f"{name} {axis}") for axis in "xyz"]
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
    camera_edited = Signal(object)  # Camera
    view_requested = Signal(str)  # a STANDARD_VIEWS name
    copy_to_script = Signal()
    bookmark_requested = Signal()  # save the current view
    bookmark_chosen = Signal(object)  # Camera
    bookmark_deleted = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.eye, self.target, self.up = VectorEdit(tr("Position")), VectorEdit(tr("Target")), VectorEdit(tr("Up"))
        self.fov = _spin(1.0, 170.0, 2, tr("Field of view"))
        self.aperture = _spin(0.0, 1e4, 4, tr("Aperture radius"))
        self.auto_focus = QCheckBox(tr("Auto (target distance)"))
        self.focus = _spin(0.0, 1e6, 3, tr("Focus distance"))
        form = QFormLayout()
        for label, widget in ((tr("Position"), self.eye), (tr("Target"), self.target), (tr("Up"), self.up),
                              (tr("Field of view °"), self.fov), (tr("Aperture"), self.aperture),
                              (tr("Focus"), self.auto_focus), ("", self.focus)):  # fmt: skip
            form.addRow(label, widget)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(form)
        layout.addLayout(self._view_buttons())
        copy = QPushButton(tr("Copy to Script"))
        copy.setToolTip(tr("Write this camera into the script (v1: 'set' lines; v2: a camera block)"))
        copy.clicked.connect(self.copy_to_script)
        layout.addWidget(copy)
        layout.addLayout(self._bookmarks(), 1)
        for edit in (self.eye, self.target, self.up):
            edit.changed.connect(self._edited)
        for spin in (self.fov, self.aperture, self.focus):
            spin.valueChanged.connect(self._edited)
        self.auto_focus.toggled.connect(self._edited)
        self._base = Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0))

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
        """Follow the viewport (without echoing the change back)."""
        self._base = camera
        widgets = [*self.eye.spins, *self.target.spins, *self.up.spins, self.fov, self.aperture, self.focus,
                   self.auto_focus]  # fmt: skip
        for w in widgets:
            w.blockSignals(True)
        self.eye.set_value(camera.eye)
        self.target.set_value(camera.target)
        self.up.set_value(camera.up)
        self.fov.setValue(camera.fov_y_deg)
        self.aperture.setValue(camera.aperture_radius)
        self.auto_focus.setChecked(camera.focus_distance is None)
        self.focus.setValue(camera.focus)
        self.focus.setEnabled(camera.focus_distance is not None)
        for w in widgets:
            w.blockSignals(False)

    def camera(self) -> Camera:
        focus = None if self.auto_focus.isChecked() else self.focus.value()
        return replace(self._base, eye=self.eye.value(), target=self.target.value(), up=self.up.value(),
                       fov_y_deg=self.fov.value(), aperture_radius=self.aperture.value(),
                       focus_distance=focus)  # fmt: skip

    def _edited(self) -> None:
        self.focus.setEnabled(not self.auto_focus.isChecked())
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
