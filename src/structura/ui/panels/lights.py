"""Lights panel (docs/14 §3 Environment & Lights): the script's v2 light blocks; add a light of any kind
(placed around the structure), remove one, or jump to it in the script. The environment and the sun are in
Render Settings."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QMenu, QPushButton, QVBoxLayout, QWidget

from ...core.scene.declarations import SceneDeclarations
from ...core.scene.light_script import KINDS
from ..i18n import tr


class LightsPanel(QWidget):
    add_requested = Signal(str)  # kind
    remove_requested = Signal(str)  # name
    go_to_requested = Signal(str)  # name

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.list = QListWidget()
        self.list.setAccessibleName(tr("Lights"))
        self.list.itemActivated.connect(lambda item: self.go_to_requested.emit(self._name(item)))
        self.list.itemDoubleClicked.connect(lambda item: self.go_to_requested.emit(self._name(item)))
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
        buttons.addWidget(remove)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.list, 1)
        layout.addLayout(buttons)

    def show_lights(self, declarations: SceneDeclarations | None) -> None:
        self.list.clear()
        if declarations is None:
            item = QListWidgetItem(tr("EisenScript v1: the sun and sky are set in Render Settings"))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(item)
            return
        for light in declarations.lights:
            summary = ", ".join(f"{k} {v}" for k, v in list(light.values.items())[:2])
            item = QListWidgetItem(f"{light.name}  ·  {light.type}" + (f"  ·  {summary}" if summary else ""))
            item.setData(Qt.ItemDataRole.UserRole, light.name)
            self.list.addItem(item)

    @staticmethod
    def _name(item: QListWidgetItem) -> str:
        return str(item.data(Qt.ItemDataRole.UserRole) or "")

    def _remove(self) -> None:
        item = self.list.currentItem()
        if item is not None and self._name(item):
            self.remove_requested.emit(self._name(item))
