# 13 — Theming

Themes in Structura are **app-wide**. One theme colours:

- the window chrome;
- every panel;
- the code editor and its syntax;
- diagnostics;
- icons;
- viewport overlays;
- the render view.

Structura ships **40 built-in themes**: 6 Nord variants and 34 other common schemes, both light and dark.
Users can create, import and share themes.

## 1. Principles

1. **Semantic roles, not widget colours.** Code never asks for "the colour of the outline panel border". It
   asks for `ui.border`. A theme maps roles to colours.
2. **Small inputs, derived outputs (DRY).** A theme author supplies a palette plus the roles they care about.
   Everything else is **derived** by documented rules in the perceptual OKLCH colour space. This keeps theme
   files short and guarantees a complete, coherent UI.
3. **Contrast is checked, not hoped for.** Every theme passes an automated WCAG check. Text roles need ≥ 4.5:1
   and UI affordances ≥ 3:1. Derived colours are auto-adjusted in lightness to meet these thresholds.
4. **Live switching.** Changing the theme never requires a restart and never rebuilds the scene.
5. **Renders do not depend on the theme.** The scene background, materials and lights come from the script and
   project only. The theme affects the viewport background only when the script sets none.

## 2. Role catalogue (`structura/themes/roles.toml`)

| Group | Roles |
|-------|-------|
| UI surfaces | `ui.bg`, `ui.bg.alt` (panels), `ui.bg.raised` (popups, menus), `ui.bg.sunken` (inputs), `ui.border`, `ui.border.strong`, `ui.shadow` |
| UI text | `ui.fg`, `ui.fg.muted`, `ui.fg.disabled`, `ui.link` |
| UI state | `ui.accent`, `ui.accent.fg`, `ui.hover`, `ui.pressed`, `ui.focus.ring`, `ui.selection.bg`, `ui.selection.fg` |
| Status | `status.success`, `status.warning`, `status.error`, `status.info`, `status.progress` |
| Tabs & bars | `tab.active.bg`, `tab.active.fg`, `tab.inactive.fg`, `tab.modified.dot`, `statusbar.bg`, `statusbar.fg`, `toolbar.bg` |
| Editor chrome | `editor.bg`, `editor.fg`, `editor.line.current`, `editor.line.number`, `editor.line.number.active`, `editor.selection`, `editor.selection.inactive`, `editor.cursor`, `editor.whitespace`, `editor.indent.guide`, `editor.bracket.match`, `editor.find.match`, `editor.find.current`, `editor.fold.marker`, `editor.sticky.bg`, `editor.inlay.fg`, `editor.inlay.bg`, `editor.rainbow.1` … `editor.rainbow.6` |
| Syntax (token roles) | `syntax.keyword` (`rule`, `set`), `syntax.operator` (`x`, `rx`, `s`, …), `syntax.modifier` (`maxdepth`, `weight`), `syntax.number`, `syntax.color` (colour literals), `syntax.primitive`, `syntax.rule.def`, `syntax.rule.ref`, `syntax.rule.undefined`, `syntax.rule.unused`, `syntax.tag`, `syntax.brace`, `syntax.bracket.arg`, `syntax.comment`, `syntax.preprocessor`, `syntax.define`, `syntax.define.substituted`, `syntax.set.key`, `syntax.set.value`, `syntax.string`, `syntax.material`, `syntax.function`, `syntax.param`, `syntax.block` (v2 block keywords) |
| Diagnostics | `diag.error`, `diag.warning`, `diag.info`, `diag.hint` |
| Viewport | `viewport.bg.top`, `viewport.bg.bottom`, `viewport.grid`, `viewport.grid.major`, `viewport.axis.x`, `viewport.axis.y`, `viewport.axis.z`, `viewport.selection`, `viewport.hover`, `viewport.hud.fg`, `viewport.hud.bg` |
| Render view | `render.checker.a`, `render.checker.b`, `render.bucket.active`, `render.bucket.done` |
| Charts | `chart.1` … `chart.8` (stats panel, generation histograms) |

Each syntax role is `{ color, bold?, italic?, underline? }`. Every other role is a colour with optional alpha.

## 3. Theme file format (TOML)

```toml
# structura/themes/builtin/nord.toml
[meta]
name        = "Nord"
id          = "nord"
kind        = "dark"             # dark | light
family      = "Nord"
author      = "Arctic Ice Studio (palette); Structura (mapping)"
license     = "MIT"
pair        = "nord-light"       # counterpart used by "follow system appearance"

[palette]                        # named colours used below; free-form
nord0  = "#2E3440"  nord1  = "#3B4252"  nord2  = "#434C5E"  nord3  = "#4C566A"
nord4  = "#D8DEE9"  nord5  = "#E5E9F0"  nord6  = "#ECEFF4"
nord7  = "#8FBCBB"  nord8  = "#88C0D0"  nord9  = "#81A1C1"  nord10 = "#5E81AC"
nord11 = "#BF616A"  nord12 = "#D08770"  nord13 = "#EBCB8B"  nord14 = "#A3BE8C"  nord15 = "#B48EAD"
comment = "#616E88"

[roles]                          # anything omitted is derived (§4)
"ui.bg"              = "nord0"
"ui.bg.alt"          = "nord1"
"ui.bg.raised"       = "nord2"
"ui.border"          = "nord3"
"ui.fg"              = "nord4"
"ui.accent"          = "nord8"
"status.error"       = "nord11"
"status.warning"     = "nord13"
"status.success"     = "nord14"

[syntax]
"syntax.keyword"       = { color = "nord9",  bold = true }
"syntax.operator"      = "nord9"
"syntax.modifier"      = { color = "nord10", italic = true }
"syntax.number"        = "nord15"
"syntax.color"         = "nord13"
"syntax.primitive"     = { color = "nord7",  bold = true }
"syntax.rule.def"      = { color = "nord8",  bold = true }
"syntax.rule.ref"      = "nord8"
"syntax.rule.undefined"= { color = "nord11", underline = true }
"syntax.tag"           = "nord12"
"syntax.comment"       = { color = "comment", italic = true }
"syntax.preprocessor"  = "nord10"
"syntax.string"        = "nord14"

[viewport]
"viewport.bg.top"    = "#3B4252"
"viewport.bg.bottom" = "#242933"
```

## 4. Derivation rules (`structura/themes/derive.py`)

Derivations work in OKLCH (perceptual lightness L, chroma C, hue h). `mix(a, b, t)` interpolates in OKLab.

| Role | Default derivation |
|------|--------------------|
| `ui.bg.alt` | `mix(ui.bg, ui.fg, 0.04)` |
| `ui.bg.raised` | `mix(ui.bg, ui.fg, 0.08)` |
| `ui.bg.sunken` | `mix(ui.bg, black or white, 0.06)` (darker in dark themes, lighter in light) |
| `ui.fg.muted` | `mix(ui.fg, ui.bg, 0.35)` |
| `ui.hover` | `ui.accent` at 12% alpha |
| `ui.selection.bg` | `ui.accent` at 30% alpha |
| `editor.*` | Follow the corresponding `ui.*` roles |
| `syntax.rule.unused` | `syntax.rule.ref` with chroma ×0.4 and L moved toward the background |
| `diag.*` | `status.*` |
| `editor.rainbow.n` | Six hues evenly spaced from `ui.accent`, with L and C fixed for contrast |
| `viewport.bg.*` | Gradient from `ui.bg.alt` to `ui.bg` |

After derivation, **contrast enforcement** runs. For each text-on-surface pair in `roles.toml`, if the
contrast ratio is below the threshold, the foreground's L is moved away from the background's in 0.01 steps
until it passes. The theme validator (`structura theme check`) reports every adjustment, so theme authors can
fix their source colours.

## 5. How a theme is applied (`ThemeService`)

One resolved `Theme` object drives all outputs. The generators are small pure functions:

| Output | Generator | Consumer |
|--------|-----------|----------|
| `QPalette` | `qt_palette.build(theme)` | Fusion style (same look on every OS) |
| Application stylesheet | `qss.render(theme)` from one Jinja2 template `app.qss.j2` | Every widget |
| Editor formats | `editor_formats.build(theme)` → `QTextCharFormat` per syntax role | Highlighter, squiggles, inlays |
| Icon tint | `icons.tint(theme)` recolours Lucide SVGs per state (normal, active, disabled) | Toolbars, panels |
| Viewport uniforms | `viewport_colors.build(theme)` | Grid, gizmo, selection outlines, HUD |
| Charts | `chart_colors.build(theme)` | Stats panel |

`ThemeService.theme_changed(Theme)` is a signal. Components restyle themselves in their slot. Switching
themes takes < 100 ms with no flicker, because it is applied inside a single `setUpdatesEnabled(False)` block.

**Follow system appearance:** on Qt ≥ 6.5, `QStyleHints.colorSchemeChanged` switches between a theme and its
`pair` (for example Nord ↔ Nord Light).

## 6. Built-in themes (40)

### 6.1 Nord variants (6)

All variants use the official Nord palette (MIT). They differ in surface depth and accent emphasis.

| Theme | Kind | Character |
|-------|------|-----------|
| **Nord** | dark | Canonical: Polar Night surfaces (nord0–3), Frost accents, Aurora for literals |
| **Nord Deep** | dark | Deeper surfaces (`#242933` bg, `#2E3440` panels). Better for long sessions and dark rooms. |
| **Nord Polar** | dark | Near-black surfaces (`#1B1F27`), high-contrast Frost text. OLED-friendly. |
| **Nord Aurora** | dark | Canonical surfaces with Aurora-forward syntax (keywords nord11, operators nord12, numbers nord15, primitives nord14). Vivid. |
| **Nord Light** | light | Snow Storm surfaces (nord6 / nord5 / nord4). Polar Night text; Frost accent nord10; Aurora literals darkened to pass contrast. |
| **Nord Frost** | light | Brighter paper-white surfaces with Frost-blue chrome (nord9/nord10) and muted Aurora literals |

### 6.2 Other dark themes (16)

| Theme | Upstream licence* |
|-------|-------------------|
| One Dark | MIT (Atom) |
| Dracula | MIT |
| Monokai (classic) | Original TextMate theme by W. Hazenberg (palette), to be verified |
| Solarized Dark | MIT |
| Gruvbox Dark | MIT |
| Tokyo Night | MIT |
| Tokyo Night Storm | MIT |
| Catppuccin Mocha | MIT |
| Catppuccin Macchiato | MIT |
| Rosé Pine | MIT |
| Everforest Dark | MIT |
| Kanagawa Wave | MIT |
| Ayu Mirage | MIT |
| GitHub Dark | MIT (Primer) |
| Night Owl | MIT |
| Oceanic Next | MIT |

### 6.3 Other light themes (14)

| Theme | Upstream licence* |
|-------|-------------------|
| One Light | MIT (Atom) |
| Solarized Light | MIT |
| Gruvbox Light | MIT |
| Tokyo Night Day | MIT |
| Catppuccin Latte | MIT |
| Rosé Pine Dawn | MIT |
| Everforest Light | MIT |
| Kanagawa Lotus | MIT |
| Ayu Light | MIT |
| GitHub Light | MIT (Primer) |
| Light Owl | MIT |
| Alucard (Dracula light) | MIT |
| Tomorrow | MIT |
| Quiet Light | MIT (VS Code) |

### 6.4 Structura originals (4)

| Theme | Kind | Purpose |
|-------|------|---------|
| **Structura Dark** | dark | The default. Neutral graphite surfaces, with a teal accent that complements typical renders. |
| **Structura Light** | light | Default light counterpart |
| High Contrast Dark | dark | Accessibility: ≥ 7:1 text contrast, bold focus rings, no reliance on hue |
| High Contrast Light | light | Accessibility, light variant |

\*Licences must be re-verified and recorded in `THIRD_PARTY_NOTICES.md` before bundling ([20](20-risks.md)
R11). Only palettes and role mappings are used, never upstream files verbatim. Commercial themes such as
Monokai Pro and the current Material Theme are deliberately excluded.

## 7. Importers & exporters

| Format | Direction | Mapping |
|--------|-----------|---------|
| Structura TOML | in/out | Native |
| **VS Code colour theme JSON** (`colors` + `tokenColors` TextMate scopes) | in | `colors` → UI roles via a mapping table (e.g. `editor.background` → `editor.bg`, `focusBorder` → `ui.focus.ring`). TextMate scopes → syntax roles by longest-prefix match (`keyword.control` → `syntax.keyword`, `constant.numeric` → `syntax.number`, `comment` → `syntax.comment`, `entity.name.function` → `syntax.rule.def`, …). Unmapped roles are derived. |
| **base16 / base24 YAML** | in | base00–base0F(+base10–17) → palette; standard base16 role mapping |
| Qt QSS | — | Not importable. QSS is generated, never authored. |

Imported themes are saved as TOML in the user themes directory and can be edited afterwards.

## 8. Theme editor (Preferences ▸ Appearance)

- A list of roles grouped as in §2, with colour pickers. A live preview pane shows a sample script, a mock
  panel, and the viewport overlay.
- "Start from accent": pick one colour and kind (dark/light), and a complete theme is generated by the
  derivation rules.
- The contrast report marks failing pairs, and "Fix automatically" is available.
- Duplicate, rename, export and delete. Built-ins are read-only and are duplicated on edit.

## 9. Fonts, density, icons

- UI font: Inter (bundled) or the system font. Code font: JetBrains Mono (bundled), or any installed
  monospace font. Sizes are independent for UI and code.
- Density: *Comfortable* (default) and *Compact*. These are spacing tokens in the QSS template, not per-widget
  values.
- Icons: Lucide SVGs, tinted per theme. Stroke width follows density.

## 10. Testing

- Each built-in theme gets a **screenshot test** of a reference window (main window + editor with all syntax
  roles + Problems panel), compared with a tolerance. This catches regressions in the QSS template.
- The contrast validator runs in CI over all built-ins, and any failure blocks the merge.
- A round-trip test imports sample VS Code and base16 themes, exports them, re-imports them, and checks they
  are identical.
