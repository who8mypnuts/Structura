"""Parse a 1.5 '.rendertemplate' XML file (docs/15 §5.1)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from xml.dom import minidom

import platformdirs

log = logging.getLogger(__name__)
LEGACY_DIR = Path(__file__).resolve().parents[2] / "resources" / "legacy" / "templates"


@dataclass(frozen=True)
class LegacyTemplate:
    name: str
    description: str = ""
    default_extension: str = "Unknown file type (*.txt)"
    run_after: str = ""
    primitives: dict[str, str] = field(default_factory=dict)  # 'box', 'box::tag', 'begin', …

    @property
    def extension(self) -> str:
        """'.pov' from 'POV-Ray scene file (*.pov)'."""
        inside = self.default_extension.rpartition("(*")[2].rstrip(")").strip()
        return inside if inside.startswith(".") else ".txt"


def _text(node: minidom.Node) -> str:
    """QDomElement::text(): CDATA kept verbatim, whitespace-only text nodes dropped (QDom's default)."""
    parts = []
    for child in node.childNodes:
        if isinstance(child, minidom.CDATASection) or (isinstance(child, minidom.Text) and child.data.strip()):
            parts.append(child.data)
        elif isinstance(child, minidom.Element):
            parts.append(_text(child))
    return "".join(parts)


def _attr(element: minidom.Element, name: str, default: str) -> str:
    return element.getAttribute(name) if element.hasAttribute(name) else default


def _primitive_name(element: minidom.Element) -> str | None:
    if element.tagName == "substitution":
        log.warning("Element-name 'substitution' is a deprecated name. Please rename to 'primitive'.")
    if not element.hasAttribute("name"):
        log.warning("Primitive without name attribute found!")
        return None
    kind = f"::{element.getAttribute('type')}" if element.hasAttribute("type") else ""
    return element.getAttribute("name") + kind


def parse_template(xml: str) -> LegacyTemplate:
    root = minidom.parseString(xml).documentElement
    if root is None:
        raise ValueError("empty template document")
    primitives: dict[str, str] = {}
    description = ""
    for child in root.childNodes:
        if not isinstance(child, minidom.Element):
            continue
        if child.tagName in ("primitive", "substitution"):
            name = _primitive_name(child)
            if name is not None:
                primitives[name] = _text(child)
        elif child.tagName == "description":
            description = _text(child)
        else:
            log.warning("Expected 'primitive' or 'description' element, found: %s", child.tagName)
    return LegacyTemplate(
        _attr(root, "name", "NONAME"),
        description,
        _attr(root, "defaultExtension", "Unknown file type (*.txt)"),
        _attr(root, "runAfter", ""),
        primitives,
    )


def load_template(path: Path) -> LegacyTemplate:
    return parse_template(path.read_text(encoding="utf-8"))


def bundled_templates() -> dict[str, Path]:
    return {p.stem: p for p in sorted(LEGACY_DIR.glob("*.rendertemplate"))}


def user_template_dir() -> Path:
    return Path(platformdirs.user_data_dir("structura")) / "templates"


def all_templates() -> dict[str, Path]:
    """The bundled templates and the user's own (edited copies; a user template shadows a bundled name)."""
    folder = user_template_dir()
    user = {p.stem: p for p in sorted(folder.glob("*.rendertemplate"))} if folder.is_dir() else {}
    return {**bundled_templates(), **user}


def save_user_template(name: str, xml: str) -> Path:
    """Validate ``xml`` (raises ValueError on a malformed template) and store it as the user template ``name``."""
    try:
        parse_template(xml)
    except Exception as exc:  # minidom raises ExpatError and friends
        raise ValueError(f"not a valid template: {exc}") from exc
    safe = "".join(ch if ch.isalnum() or ch in " -_." else "_" for ch in name).strip() or "template"
    path = user_template_dir() / f"{safe}.rendertemplate"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(xml, encoding="utf-8")
    return path
