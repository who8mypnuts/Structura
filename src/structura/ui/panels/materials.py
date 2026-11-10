"""Materials panel (docs/14 §3): the tags of the built structure and the material each one renders with
(declared in the script, a preset named like the tag, or the default). Edit a material with a live swatch,
then write it into the script as a v2 'material' block. The editable fields come from
core.scene.material.material_param_specs (the debug models stay script-only)."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.scene.ir import SceneIR
from ...core.scene.material import STATE, Material, MaterialModel, material_param_specs, presets
from ..i18n import tr
from ..widgets.color_button import ColorButton
from ..widgets.param_form import ParamForm

NONE = "—"
SPECS = material_param_specs()


def form_values(material: Material) -> dict[str, Any]:
    """The panel's values of ``material`` (the model by name, no absorption as distance 0, 'state' opacity as 1)."""
    values: dict[str, Any] = {s.key: getattr(material, s.key) for s in SPECS}
    values["model"] = material.model.name.lower()
    values["attenuation_distance"] = 0.0 if math.isinf(material.attenuation_distance) else material.attenuation_distance
    values["opacity"] = 1.0 if isinstance(material.opacity, str) else float(material.opacity)
    return values


def material_values(values: dict[str, Any], own_alpha: bool) -> dict[str, Any]:
    """form_values, inverted: Material fields from the panel's values."""
    out = dict(values)
    out["model"] = MaterialModel[str(values["model"]).upper()]
    out["attenuation_distance"] = float(values["attenuation_distance"]) or math.inf
    out["opacity"] = STATE if own_alpha else float(values["opacity"])
    return out


def _rgb(color: QColor) -> tuple[float, float, float]:
    return (color.redF(), color.greenF(), color.blueF())


def _qcolor(value: object, fallback: str = "#c8c8c8") -> QColor:
    if isinstance(value, tuple):
        return QColor.fromRgbF(*(float(c) for c in value))
    return QColor(fallback)


class MaterialsPanel(QWidget):
    apply_requested = Signal(object, str)  # Material, preset name
    preview_requested = Signal(object)  # Material: render a swatch

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.list = QListWidget()
        self.list.setAccessibleName(tr("Tags and materials"))
        self.list.currentItemChanged.connect(self._select)
        self.preset = QComboBox()
        self.preset.setAccessibleName(tr("Preset"))
        self.preset.addItems([NONE, *sorted(presets())])
        self.own_colour = QCheckBox(tr("Use the structure's colours"))
        self.own_alpha = QCheckBox(tr("Use the structure's transparency (alpha)"))
        self.base, self.emission = ColorButton(), ColorButton(QColor("#ffffff"))
        self.absorption = ColorButton(QColor("#ffffff"))
        self.absorption.setToolTip(tr("Absorption colour: what white light becomes inside glass after the distance"))
        self.form = ParamForm(tuple(replace(s, label=tr(s.title)) for s in SPECS), {})
        self.swatch = QLabel()
        self.swatch.setMinimumHeight(96)
        self.swatch.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.write = QPushButton(tr("Write to Script"))
        self.write.setToolTip(tr("Add or update this tag's 'material' block (EisenScript v2)"))
        self.write.clicked.connect(lambda: self.apply_requested.emit(self.material(), self._preset()))
        form = QFormLayout()
        for label, widget in ((tr("Preset"), self.preset), ("", self.own_colour), (tr("Base colour"), self.base),
                              (tr("Emission colour"), self.emission), (tr("Absorption colour"), self.absorption),
                              ("", self.own_alpha)):  # fmt: skip
            form.addRow(label, widget)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.list, 1)
        layout.addWidget(self.swatch)
        layout.addLayout(form)
        layout.addWidget(self.form)
        layout.addWidget(self.write)
        self.current = Material()
        self.declared: dict[str, Material] = {}
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)
        self._debounce.timeout.connect(lambda: self.preview_requested.emit(self.material()))
        self.preset.currentTextChanged.connect(self._preset_chosen)
        for signal in (self.own_colour.toggled, self.own_alpha.toggled, self.base.changed, self.emission.changed,
                       self.absorption.changed, self.form.changed):  # fmt: skip
            signal.connect(self._edited)
        self.setEnabled(False)

    # -- the scene ---------------------------------------------------------------------------------------------
    def show_scene(self, scene: SceneIR | None) -> None:
        """List the scene's tags (with how many objects carry each) and the script's declared materials."""
        selected = self.list.currentItem().data(Qt.ItemDataRole.UserRole) if self.list.currentItem() else None
        self.list.clear()
        self.declared = dict(scene.declarations.materials) if scene is not None and scene.declarations else {}
        names: dict[str, int] = {}
        if scene is not None:
            counts = np.bincount(scene.tag, minlength=len(scene.tags)) if len(scene) else np.zeros(len(scene.tags))
            names = {name: int(counts[i]) for i, name in enumerate(scene.tags) if name}
        for name in sorted({*names, *self.declared}):
            source = tr("declared") if name in self.declared else tr("preset") if name in presets() else tr("default")
            item = QListWidgetItem(f"{name}  ·  {names.get(name, 0):,} objects  ·  {source}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list.addItem(item)
            if name == selected:
                self.list.setCurrentItem(item)
        self.setEnabled(self.list.count() > 0)

    def _select(self, item: QListWidgetItem | None) -> None:
        if item is None:
            return
        name = str(item.data(Qt.ItemDataRole.UserRole))
        material = self.declared.get(name) or presets().get(name) or Material()
        self.show_material(replace(material, name=name), name if name in presets() else "")

    def show_material(self, material: Material, preset: str) -> None:
        self.current = material
        widgets = (self.preset, self.own_colour, self.own_alpha, self.base, self.emission, self.absorption, self.form)
        for w in widgets:
            w.blockSignals(True)
        self.preset.setCurrentText(preset or NONE)
        self.own_colour.setChecked(material.base == STATE)
        self.own_alpha.setChecked(material.opacity == STATE)
        self.base.set_color(_qcolor(material.base))
        self.emission.set_color(_qcolor(material.emission, "#ffffff"))
        self.absorption.set_color(_qcolor(material.attenuation_color, "#ffffff"))
        self.form.set_values(form_values(material))
        for w in widgets:
            w.blockSignals(False)
        self._enable()
        self._debounce.start()

    # -- editing -------------------------------------------------------------------------------------------
    def _preset(self) -> str:
        text = self.preset.currentText()
        return "" if text == NONE else text

    def _preset_chosen(self) -> None:
        start = presets().get(self._preset(), Material())
        self.show_material(replace(start, name=self.current.name), self._preset())

    def _enable(self) -> None:
        self.base.setEnabled(not self.own_colour.isChecked())
        self.form.widgets["opacity"].setEnabled(not self.own_alpha.isChecked())

    def _edited(self, *_: object) -> None:
        self._enable()
        self.current = self.material()
        self._debounce.start()

    def material(self) -> Material:
        values = material_values(self.form.values(), self.own_alpha.isChecked())
        base = STATE if self.own_colour.isChecked() else self._kept(self.current.base, self.base.color)
        emission = self._kept(self.current.emission, self.emission.color) if values["emission_strength"] > 0 \
            else self.current.emission  # fmt: skip
        kept = self._kept(self.current.attenuation_color, self.absorption.color)
        absorption = kept if isinstance(kept, tuple) else self.current.attenuation_color
        return replace(self.current, base=base, emission=emission, attenuation_color=absorption, **values)

    @staticmethod
    def _kept(value: str | tuple[float, float, float], shown: QColor) -> str | tuple[float, float, float]:
        """The material's own colour while the button still shows it (8-bit buttons must not round it)."""
        return value if isinstance(value, tuple) and _qcolor(value) == shown else _rgb(shown)

    def show_swatch(self, rgb: np.ndarray) -> None:
        rgb = np.ascontiguousarray(rgb)
        h, w, _ = rgb.shape
        self.swatch.setPixmap(QPixmap.fromImage(QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()))
