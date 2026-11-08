"""Editor view options (docs/12 §2.1): one frozen value applied to every CodeEditor. The ParamSpecs are the
single declaration: Preferences shows them, View-menu toggles flip them, settings store them."""

from __future__ import annotations

from dataclasses import dataclass, fields

from ...core.params import ParamSpec, ParamType
from ...services.settings import SettingsService

PREFIX = "editor/"


@dataclass(frozen=True)
class EditorOptions:
    code_size: int = 11
    word_wrap: bool = False
    show_whitespace: bool = False
    indent_guides: bool = True
    rainbow_brackets: bool = False
    minimap: bool = True
    sticky_scroll: bool = True
    breadcrumbs: bool = True
    vim: bool = False


LABELS = {
    "code_size": "Code font size",
    "word_wrap": "Word wrap",
    "show_whitespace": "Show whitespace",
    "indent_guides": "Indentation guides",
    "rainbow_brackets": "Rainbow brackets",
    "minimap": "Minimap",
    "sticky_scroll": "Sticky scroll (pin the current rule header)",
    "breadcrumbs": "Breadcrumbs (the rule at the cursor)",
    "vim": "Vim keybindings (normal, insert and visual modes)",
}
TOGGLES = ("word_wrap", "show_whitespace", "indent_guides", "rainbow_brackets", "minimap", "sticky_scroll",
           "breadcrumbs", "vim")  # fmt: skip


def option_specs() -> tuple[ParamSpec, ...]:
    defaults = EditorOptions()
    specs = []
    for f in fields(EditorOptions):
        value = getattr(defaults, f.name)
        if isinstance(value, bool):
            specs.append(ParamSpec(PREFIX + f.name, ParamType.BOOL, value, LABELS[f.name]))
        else:
            specs.append(ParamSpec(PREFIX + f.name, ParamType.INT, value, LABELS[f.name], range=(6, 40)))
    return tuple(specs)


def load_options(settings: SettingsService) -> EditorOptions:
    defaults = EditorOptions()
    values = {f.name: settings.value(PREFIX + f.name, getattr(defaults, f.name)) for f in fields(EditorOptions)}
    return EditorOptions(**values)


def toggle_option(settings: SettingsService, name: str) -> EditorOptions:
    """Flip one boolean option and return the new options."""
    current = load_options(settings)
    settings.set_value(PREFIX + name, not getattr(current, name))
    return load_options(settings)
