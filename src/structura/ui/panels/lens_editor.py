"""The lens part of the Camera panel (PLAN Q5): simple by default, everything on demand.

Simple: a lens preset, the focal length (two-way with the field of view), a Depth of field switch and amount
(an f-stop from f/22 to f/1.2), where to focus, and a readout of the sharp range. Advanced (a collapsible
group): projection, sensor, f-stop or aperture radius, the scene's scale, bokeh (blades, bias, anamorphic),
lens shift and tilt, and the orthographic / fisheye settings. All of it edits core.scene.lens.Lens."""

from __future__ import annotations

import math
from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...core.scene.camera import LEGACY_FOV, Camera
from ...core.scene.lens import (
    FISHEYE_MAPPINGS,
    FOCUS_MODES,
    LENS_PRESETS,
    PROJECTIONS,
    SENSORS,
    Lens,
    amount_for_fstop,
    focal_length_mm,
    fov_for,
    fstop_for_amount,
)
from ..i18n import tr
from ..widgets.fields import combo_box, spin_box, spin_pair

CUSTOM, LEGACY = "Custom", "Structure Synth 22°"
DEFAULT_AMOUNT = 0.5


class LensEditor(QWidget):
    """The Camera panel's lens: simple (preset, focal length, depth of field, focus) and advanced (projection,
    sensor, aperture, scale, bokeh, shift and tilt). Edits build a core.scene.lens.Lens; ``changed`` says so.
    """

    changed = Signal()  # the user edited the lens or the field of view
    focus_selection = Signal()  # "On selection": focus on the object selected in the viewport

    def __init__(self, parent: QWidget | None = None) -> None:
        """Builds the simple rows and the (folded) advanced group.

        Args:
            parent: The parent widget.
        """
        super().__init__(parent)
        self._camera = Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0))
        self._scene_size = 0.0  # the structure's diagonal in world units (scene scale helper)
        self._radius_mode = False  # the lens has an aperture radius and no f-stop (v2 'aperture', legacy 'dof')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._simple())
        layout.addWidget(self._advanced())
        self._connect()

    # -- building ------------------------------------------------------------------------------------------
    def _simple(self) -> QFormLayout:
        """The simple rows: lens preset, focal length ↔ field of view, depth of field, focus and the readout."""
        self.preset = combo_box([CUSTOM, *LENS_PRESETS, LEGACY], tr("Lens preset"))
        self.focal = spin_box(2.0, 2000.0, 1, tr("Focal length"), " mm")
        self.fov = spin_box(1.0, 170.0, 2, tr("Field of view"), "°")
        self.dof = QCheckBox(tr("Depth of field"))
        self.amount = QSlider(Qt.Orientation.Horizontal)
        self.amount.setRange(0, 100)
        self.amount.setAccessibleName(tr("Depth of field amount"))
        self.amount.setToolTip(tr("Deep (f/22) … shallow (f/1.2)"))
        self.focus_mode = combo_box(("target", "manual", "hyperfocal"), tr("Focus"))
        self.focus_mode.setToolTip(
            tr(
                "Target: the point looked at · Manual: the distance below (Alt+click in the "
                "viewport) · Hyperfocal: sharp from half that distance to infinity"
            )
        )
        self.focus = spin_box(0.0, 1e6, 3, tr("Focus distance"))
        self.on_selection = QPushButton(tr("On Selection"))
        self.on_selection.setToolTip(tr("Focus on the object selected in the viewport"))
        focus_row = QHBoxLayout()
        focus_row.addWidget(self.focus_mode)
        focus_row.addWidget(self.focus, 1)
        focus_row.addWidget(self.on_selection)
        self.readout = QLabel()
        self.readout.setObjectName("Muted")
        self.readout.setWordWrap(True)
        form = QFormLayout()
        rows = ((tr("Lens"), self.preset), (tr("Focal length"), self.focal), (tr("Field of view"), self.fov),
                ("", self.dof), (tr("Shallow"), self.amount))  # fmt: skip
        for label, widget in rows:
            form.addRow(label, widget)
        form.addRow(tr("Focus"), focus_row)
        form.addRow("", self.readout)
        return form

    def _advanced(self) -> QGroupBox:
        """The advanced group (folded at first): every other lens field."""
        box = QGroupBox(tr("Advanced lens"))
        box.setCheckable(True)
        box.setChecked(False)
        inner = QWidget()
        form = QFormLayout(inner)
        self.projection = combo_box(PROJECTIONS, tr("Projection"))
        self.sensor = combo_box([*SENSORS, CUSTOM], tr("Sensor"))
        sensor_row, self.sensor_w, self.sensor_h = spin_pair(tr("Sensor size (mm)"), 1.0, 200.0, 2)
        self.fstop = spin_box(0.5, 128.0, 2, tr("f-stop"))
        self.radius = spin_box(0.0, 1e4, 4, tr("Aperture radius"))
        self.units = spin_box(1e-4, 1e6, 4, tr("World units per metre"))
        self.size_m = spin_box(0.0, 1e6, 3, tr("Structure size"), " m")
        self.size_m.setToolTip(tr("How big the structure is in the real world: sets the scale the f-stop uses"))
        self.blades = spin_box(0, 16, 0, tr("Aperture blades"))
        self.blade_rotation = spin_box(-360.0, 360.0, 1, tr("Blade rotation"), "°")
        self.bias = spin_box(-1.0, 1.0, 2, tr("Bokeh bias"))
        self.anamorphic = spin_box(0.25, 4.0, 2, tr("Anamorphic ratio"))
        shift_row, self.shift_x, self.shift_y = spin_pair(tr("Lens shift"), -2.0, 2.0)
        tilt_row, self.tilt_x, self.tilt_y = spin_pair(tr("Focus tilt"), -60.0, 60.0, 2)
        self.ortho = spin_box(1e-4, 1e6, 3, tr("Orthographic height"))
        self.fisheye = spin_box(1.0, 360.0, 1, tr("Fisheye field"), "°")
        self.mapping = combo_box(FISHEYE_MAPPINGS, tr("Fisheye mapping"))
        rows = ((tr("Projection"), self.projection), (tr("Sensor"), self.sensor), ("", sensor_row),
                (tr("f-stop"), self.fstop), (tr("Aperture radius"), self.radius), (tr("Units per metre"), self.units),
                (tr("Structure size"), self.size_m), (tr("Blades"), self.blades),
                (tr("Blade rotation"), self.blade_rotation), (tr("Bokeh bias"), self.bias),
                (tr("Anamorphic"), self.anamorphic), (tr("Shift (x, y)"), shift_row), (tr("Tilt (x, y)"), tilt_row),
                (tr("Ortho height"), self.ortho), (tr("Fisheye field"), self.fisheye),
                (tr("Mapping"), self.mapping))  # fmt: skip
        for label, widget in rows:
            form.addRow(label, widget)
        column = QVBoxLayout(box)
        column.setContentsMargins(4, 4, 4, 4)
        column.addWidget(inner)
        box.toggled.connect(inner.setVisible)
        inner.setVisible(False)
        self.advanced = box
        return box

    def _connect(self) -> None:
        """Wires the fields: two-way focal length ↔ field of view and f-stop ↔ slider; others to ``_edited``."""
        self.preset.currentTextChanged.connect(self._preset_chosen)
        self.focal.valueChanged.connect(self._focal_edited)
        self.fov.valueChanged.connect(self._fov_edited)
        self.size_m.valueChanged.connect(self._size_edited)
        self.on_selection.clicked.connect(self.focus_selection)
        self.amount.sliderReleased.connect(self._amount_edited)
        self.amount.valueChanged.connect(lambda _v: None if self.amount.isSliderDown() else self._amount_edited())
        self.fstop.valueChanged.connect(self._fstop_edited)
        self.radius.valueChanged.connect(self._radius_edited)
        self.dof.toggled.connect(self._edited)
        for box in (self.focus_mode, self.projection, self.sensor, self.mapping):
            box.currentTextChanged.connect(self._edited)
        for widget in (self.focus, self.sensor_w, self.sensor_h, self.units, self.blades,
                       self.blade_rotation, self.bias, self.anamorphic, self.shift_x, self.shift_y, self.tilt_x,
                       self.tilt_y, self.ortho, self.fisheye):  # fmt: skip
            widget.valueChanged.connect(self._edited)

    # -- showing -------------------------------------------------------------------------------------------
    def widgets(self) -> list[QWidget]:
        """Returns every input field (to block their signals while showing a camera)."""
        kinds = (QDoubleSpinBox, QComboBox, QCheckBox, QSlider)
        return [w for w in self.findChildren(QWidget) if isinstance(w, kinds)]

    def show_camera(self, camera: Camera) -> None:
        """Shows a camera's lens without echoing the change back.

        Args:
            camera: The camera the viewport has now.
        """
        self._camera = camera
        lens = camera.lens
        for w in self.widgets():
            w.blockSignals(True)
        self.focal.setValue(camera.focal_length_mm)
        self.fov.setValue(camera.fov_y_deg)
        self.preset.setCurrentText(self._preset_of(camera))
        self.dof.setChecked(lens.depth_of_field)
        self.amount.setValue(round(100 * amount_for_fstop(camera.fstop if math.isfinite(camera.fstop) else 22.0)))
        self.focus_mode.setCurrentText(lens.focus_mode)
        self.focus.setValue(camera.focus)
        self.projection.setCurrentText(lens.projection)
        name = next((n for n, size in SENSORS.items() if size == lens.sensor_mm), CUSTOM)
        self.sensor.setCurrentText(name)
        self.sensor_w.setValue(lens.sensor_mm[0])
        self.sensor_h.setValue(lens.sensor_mm[1])
        self.fstop.setValue(lens.fstop or (camera.fstop if math.isfinite(camera.fstop) else 8.0))
        self._radius_mode = lens.fstop is None and lens.aperture_radius > 0
        self.radius.setValue(lens.aperture_radius)
        self.units.setValue(lens.units_per_metre)
        self.size_m.setValue(self._scene_size / lens.units_per_metre if self._scene_size else 0.0)
        for widget, value in ((self.blades, lens.blades), (self.blade_rotation, lens.blade_rotation_deg),
                              (self.bias, lens.bokeh_bias), (self.anamorphic, lens.anamorphic),
                              (self.shift_x, lens.shift[0]), (self.shift_y, lens.shift[1]),
                              (self.tilt_x, lens.tilt[0]), (self.tilt_y, lens.tilt[1]),
                              (self.ortho, lens.ortho_height), (self.fisheye, lens.fisheye_fov_deg)):  # fmt: skip
            widget.setValue(value)
        self.mapping.setCurrentText(lens.fisheye_mapping)
        for w in self.widgets():
            w.blockSignals(False)
        self._enable()
        self._readout(camera)

    def set_scene_size(self, diagonal: float) -> None:
        """Tells the editor the structure's size, for the 'Structure size' helper (metres ↔ units per metre).

        Args:
            diagonal: The structure's bounding-box diagonal in world units (0: unknown).
        """
        self._scene_size = diagonal
        self.size_m.blockSignals(True)
        self.size_m.setValue(diagonal / self._camera.lens.units_per_metre if diagonal else 0.0)
        self.size_m.blockSignals(False)

    @staticmethod
    def _preset_of(camera: Camera) -> str:
        if abs(camera.fov_y_deg - LEGACY_FOV) < 1e-6:
            return LEGACY
        return next((n for n, mm in LENS_PRESETS.items() if abs(camera.focal_length_mm - mm) < 0.05), CUSTOM)

    def _enable(self) -> None:
        """Enables only the fields the projection, depth of field, focus mode and sensor make meaningful."""
        perspective = self.projection.currentText() == "perspective"
        dof = self.dof.isChecked() and perspective
        for widget in (self.amount, self.focus_mode, self.fstop, self.blades, self.blade_rotation, self.bias,
                       self.anamorphic, self.tilt_x, self.tilt_y):  # fmt: skip
            widget.setEnabled(dof)
        self.focus.setEnabled(dof and self.focus_mode.currentText() == "manual")
        self.on_selection.setEnabled(dof)
        self.radius.setEnabled(dof)
        self.ortho.setEnabled(self.projection.currentText() == "orthographic")
        self.fisheye.setEnabled(self.projection.currentText() == "fisheye")
        self.mapping.setEnabled(self.projection.currentText() == "fisheye")
        custom = self.sensor.currentText() == CUSTOM
        self.sensor_w.setEnabled(custom)
        self.sensor_h.setEnabled(custom)

    def _readout(self, camera: Camera) -> None:
        """Shows the f-stop, focus and sharp range (or why there is no depth of field)."""
        if camera.lens.projection != "perspective":
            self.readout.setText(tr("No depth of field in this projection"))
        elif camera.aperture_radius <= 0:
            self.readout.setText(tr("Pinhole: everything is sharp"))
        else:
            near, far = camera.sharp_range
            far_text = "∞" if math.isinf(far) else f"{far:.3g}"
            self.readout.setText(
                tr("f/{f:.2g} · focus {d:.3g} · sharp from {near:.3g} to {far}").format(
                    f=camera.fstop, d=camera.focus, near=near, far=far_text
                )
            )

    # -- editing -------------------------------------------------------------------------------------------
    def _preset_chosen(self, name: str) -> None:
        if name == CUSTOM:
            return
        fov = LEGACY_FOV if name == LEGACY else fov_for(LENS_PRESETS[name], self._sensor()[1])
        self.fov.setValue(fov)  # the focal length follows; one 'changed'

    def _focal_edited(self, mm: float) -> None:
        self.fov.blockSignals(True)
        self.fov.setValue(fov_for(mm, self._sensor()[1]))
        self.fov.blockSignals(False)
        self._edited()

    def _fov_edited(self, degrees: float) -> None:
        self.focal.blockSignals(True)
        self.focal.setValue(focal_length_mm(degrees, self._sensor()[1]))
        self.focal.blockSignals(False)
        self._edited()

    def _amount_edited(self) -> None:
        self._radius_mode = False
        self.fstop.blockSignals(True)
        self.fstop.setValue(fstop_for_amount(self.amount.value() / 100))
        self.fstop.blockSignals(False)
        self._edited()

    def _fstop_edited(self, fstop: float) -> None:
        self._radius_mode = False
        self.amount.blockSignals(True)
        self.amount.setValue(round(100 * amount_for_fstop(fstop)))
        self.amount.blockSignals(False)
        self._edited()

    def _radius_edited(self, _radius: float) -> None:
        self._radius_mode = True
        self._edited()

    def _size_edited(self, metres: float) -> None:
        if metres > 0 and self._scene_size > 0:
            self.units.setValue(self._scene_size / metres)  # → _edited

    def _sensor(self) -> tuple[float, float]:
        name = self.sensor.currentText()
        return SENSORS[name] if name in SENSORS else (self.sensor_w.value(), self.sensor_h.value())

    def _edited(self, *_: object) -> None:
        """Any edit: re-enable fields, refresh the readout and the preset, and emit ``changed``."""
        self._enable()
        camera = self.camera()
        self._camera = camera
        self._readout(camera)
        self.preset.blockSignals(True)
        self.preset.setCurrentText(self._preset_of(camera))
        self.preset.blockSignals(False)
        self.changed.emit()

    def lens(self) -> Lens:
        """Returns the lens the fields describe (an aperture radius only while one was set instead of an f-stop)."""
        dof = self.dof.isChecked()
        radius = self.radius.value() if dof and self._radius_mode else 0.0
        fstop = self.fstop.value() if dof and not radius else None
        focus_mode = self.focus_mode.currentText() if self.focus_mode.currentText() in FOCUS_MODES else "target"
        return replace(
            self._camera.lens, projection=self.projection.currentText(), sensor_mm=self._sensor(), fstop=fstop,
            aperture_radius=radius, focus_mode=focus_mode,
            focus_distance=self.focus.value() if focus_mode == "manual" else None,
            blades=int(self.blades.value()), blade_rotation_deg=self.blade_rotation.value(),
            bokeh_bias=self.bias.value(), anamorphic=self.anamorphic.value(),
            shift=(self.shift_x.value(), self.shift_y.value()), tilt=(self.tilt_x.value(), self.tilt_y.value()),
            ortho_height=self.ortho.value(), fisheye_fov_deg=self.fisheye.value(),
            fisheye_mapping=self.mapping.currentText(), units_per_metre=self.units.value(),
        )  # fmt: skip

    def camera(self) -> Camera:
        """Returns the shown camera with this editor's field of view and lens."""
        return replace(self._camera, fov_y_deg=self.fov.value(), lens=self.lens())
