"""Lights panel (docs/14 §3 Environment & Lights): the script's v2 light blocks. Add a light of any kind
(placed around the structure) or a whole lighting rig (core/scene/light_rigs.py), remove one, jump to it in
the script, or edit its values in a form generated from the language catalogue (core/lang/v2/block_form.py)
— the block is rewritten in the script, which stays the single source of truth. The environment and the sun
of v1 scripts are in Render Settings."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.lang.v2.block_form import block_specs, form_values
from ...core.scene.declarations import LightSpec, SceneDeclarations
from ...core.scene.light_rigs import rigs
from ...core.scene.light_script import KINDS
from ..i18n import tr
from ..widgets.param_form import ParamForm

EDIT_DELAY_MS = 400  # edits are written to the script once typing pauses


class LightsPanel(QWidget):
    add_requested = Signal(str)  # kind
    remove_requested = Signal(str)  # name
    go_to_requested = Signal(str)  # name
    edit_requested = Signal(str, dict)  # name, the block's entries (type included)
    rig_requested = Signal(str)  # a lighting rig's name (core/scene/light_rigs.toml)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.list = QListWidget()
        self.list.setAccessibleName(tr("Lights"))
        self.list.itemActivated.connect(lambda item: self.go_to_requested.emit(self._name(item)))
        self.list.itemDoubleClicked.connect(lambda item: self.go_to_requested.emit(self._name(item)))
        self.list.currentItemChanged.connect(lambda *_: self._show_selected())
        add = QPushButton(tr("Add Light"))
        menu = QMenu(add)
        titles = {"sun": tr("Sun"), "point": tr("Point"), "sphere": tr("Sphere"), "spot": tr("Spot"),
                  "rect": tr("Area (rectangle)")}  # fmt: skip
        for kind in KINDS:
            menu.addAction(titles[kind]).triggered.connect(lambda _=False, k=kind: self.add_requested.emit(k))
        add.setMenu(menu)
        remove = QPushButton(tr("Remove"))
        remove.clicked.connect(self._remove)
        buttons = QHBoxLayout()
        buttons.addWidget(add)
        buttons.addWidget(self._rig_button())
        buttons.addWidget(remove)
        self.hint = QLabel(tr("Select a light to edit it; the light block in the script is updated."))
        self.hint.setObjectName("Muted")
        self.hint.setWordWrap(True)
        self.form_box = QVBoxLayout()
        self.form: ParamForm | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.list, 1)
        layout.addLayout(buttons)
        layout.addWidget(self.hint)
        layout.addLayout(self.form_box)
        self.lights: dict[str, LightSpec] = {}
        self.edited: dict[str, Any] = {}  # the selected light's entries, with the user's edits
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(EDIT_DELAY_MS)
        self._timer.timeout.connect(self._emit_edit)

    def _rig_button(self) -> QPushButton:
        button = QPushButton(tr("Lighting Rig"))
        button.setToolTip(tr("Light the structure with a complete set-up: lights and environment, sized to it "
                             "(applying another rig replaces the rig's lights; your own lights stay)"))  # fmt: skip
        menu = QMenu(button)
        menu.setToolTipsVisible(True)
        for rig in rigs().values():
            action = menu.addAction(tr(rig.name))
            action.setToolTip(tr(rig.doc))
            action.triggered.connect(lambda _=False, name=rig.name: self.rig_requested.emit(name))
        button.setMenu(menu)
        return button

    def show_lights(self, declarations: SceneDeclarations | None) -> None:
        selected = self._name(self.list.currentItem()) if self.list.currentItem() else ""
        self.list.blockSignals(True)
        self.list.clear()
        self.lights = {light.name: light for light in declarations.lights} if declarations is not None else {}
        if declarations is None:
            item = QListWidgetItem(tr("EisenScript v1: the sun and sky are set in Render Settings"))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(item)
        for light in self.lights.values():
            summary = ", ".join(f"{k} {v}" for k, v in list(light.values.items())[:2])
            item = QListWidgetItem(f"{light.name}  ·  {light.type}" + (f"  ·  {summary}" if summary else ""))
            item.setData(Qt.ItemDataRole.UserRole, light.name)
            self.list.addItem(item)
            if light.name == selected:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        if not self._timer.isActive():  # never replace a form the user is typing in
            self._show_selected()

    @staticmethod
    def _name(item: QListWidgetItem | None) -> str:
        return str(item.data(Qt.ItemDataRole.UserRole) or "") if item is not None else ""

    def selected(self) -> LightSpec | None:
        return self.lights.get(self._name(self.list.currentItem()))

    def _show_selected(self) -> None:
        light = self.selected()
        if self.form is not None:
            self.form.deleteLater()
            self.form = None
        self.hint.setVisible(light is None and bool(self.lights))
        if light is None:
            return
        self.edited = {"type": light.type, **light.values}
        specs = block_specs("light", light.type)
        self.form = ParamForm(tuple(s for s in specs if s.key != "type"), form_values(specs, self.edited))
        self.form.setAccessibleName(tr("Light properties"))
        self.form.changed.connect(self._changed)
        self.form_box.addWidget(self.form)

    def _changed(self, key: str, value: object) -> None:
        self.edited[key] = value
        self._timer.start()

    def _emit_edit(self) -> None:
        light = self.selected()
        if light is not None:
            self.edit_requested.emit(light.name, dict(self.edited))

    def _remove(self) -> None:
        item = self.list.currentItem()
        if item is not None and self._name(item):
            self.remove_requested.emit(self._name(item))
