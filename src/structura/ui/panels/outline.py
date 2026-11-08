"""Outline panel (docs/14 §3): the rules of the active document, with a filter. Ambiguous rules (several
definitions of one name) are grouped, each alternative with its weight and the chance it is chosen. Click to
jump to a definition."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLineEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ...core.lang.analysis import Analysis, RuleSymbol
from ..i18n import tr


class OutlinePanel(QWidget):
    activated_offset = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(tr("Filter rules"))
        self.filter.setAccessibleName(tr("Filter rules"))
        self.tree = QTreeWidget()
        self.tree.setAccessibleName(tr("Rules"))
        self.tree.setHeaderLabels([tr("Rule"), tr("Weight"), tr("Uses")])
        self.tree.itemClicked.connect(self._clicked)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.filter)
        layout.addWidget(self.tree, 1)
        self.filter.textChanged.connect(self._refilter)

    def _clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        offset = item.data(0, Qt.ItemDataRole.UserRole)
        if offset is not None:
            self.activated_offset.emit(int(offset))

    def show_analysis(self, analysis: Analysis) -> None:
        self.tree.clear()
        groups: dict[str, list[RuleSymbol]] = {}
        for rule in analysis.rules:
            groups.setdefault(rule.name, []).append(rule)
        for name, rules in groups.items():
            uses = str(len(analysis.references.get(name, ())))
            if len(rules) == 1:
                self.tree.addTopLevelItem(self._item([name, f"{rules[0].weight:g}", uses], rules[0].span.start))
                continue
            parent = self._item([f"{name}  ×{len(rules)}", "", uses], rules[0].span.start)
            total = sum(r.weight for r in rules) or 1.0
            for n, rule in enumerate(rules, 1):
                chance = f"{rule.weight:g} · {100 * rule.weight / total:.0f} %"
                parent.addChild(self._item([f"{name} #{n}", chance, ""], rule.span.start))
            self.tree.addTopLevelItem(parent)
            parent.setExpanded(True)
        self._refilter()

    @staticmethod
    def _item(columns: list[str], offset: int) -> QTreeWidgetItem:
        item = QTreeWidgetItem(columns)
        item.setData(0, Qt.ItemDataRole.UserRole, offset)
        return item

    def _refilter(self) -> None:
        needle = self.filter.text().lower()
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item is not None:
                item.setHidden(bool(needle) and needle not in item.text(0).lower())
