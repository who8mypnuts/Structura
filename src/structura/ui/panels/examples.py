"""Examples panel: the bundled legacy and community scripts, searchable; activate to open (docs/14 §3)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLineEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

RESOURCES = Path(__file__).resolve().parents[2] / "resources"
SOURCES = (  # (group, folder, sub-folders become their own groups)
    ("Classic", RESOURCES / "legacy" / "examples", True),
    ("Community", RESOURCES / "examples" / "community", False),
)


def example_files() -> list[tuple[str, Path]]:
    found = []
    for group, root, nested in SOURCES:
        for path in sorted(root.rglob("*.es"), key=lambda p: p.stem.lower()):
            rel = path.relative_to(root)
            found.append((f"{group} · {rel.parts[0]}" if nested and len(rel.parts) > 1 else group, path))
    return found


class ExamplesPanel(QWidget):
    open_example = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search examples")
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.search)
        layout.addWidget(self.tree, 1)
        groups: dict[str, QTreeWidgetItem] = {}
        for group, path in example_files():
            if group not in groups:
                groups[group] = QTreeWidgetItem(self.tree, [group])
            item = QTreeWidgetItem(groups[group], [path.stem])
            item.setData(0, Qt.ItemDataRole.UserRole, str(path))
        self.search.textChanged.connect(self._filter)
        self.tree.itemActivated.connect(self._activate)
        self.tree.itemDoubleClicked.connect(self._activate)

    def _filter(self, text: str) -> None:
        needle = text.lower()
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            if group is None:
                continue
            visible = 0
            for j in range(group.childCount()):
                child = group.child(j)
                if child is None:
                    continue
                hide = bool(needle) and needle not in child.text(0).lower()
                child.setHidden(hide)
                visible += not hide
            group.setHidden(visible == 0)
            group.setExpanded(bool(needle))

    def _activate(self, item: QTreeWidgetItem, _column: int = 0) -> None:
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path:
            self.open_example.emit(Path(path))
