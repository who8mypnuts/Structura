# The editor

## Writing

- **Completion** pops up as you type: rules, primitives, operators, settings, colours, v2 block keys and
  functions, and snippets. Tab or Enter accepts; snippet fields are visited with Tab.
- **Signature help** shows an operator's or function's arguments while you type them.
- **Hover** a word for its documentation; hover a rule call to highlight the objects it made in the viewport.
- **Diagnostics** underline errors and warnings as you type; the **Problems** panel lists them — every broken
  rule at once, while the rules that parse stay available to the outline and completion. **Ctrl+.** offers
  quick fixes (create a missing rule, fix a spelling, convert an alias …).
- **Inlay hints** show loop counts, the chance of each alternative of a rule, the material a tag resolves to,
  and after each top-level call an **estimate of the objects** it makes ("≈ 1.2k objects", "(limit)" when the
  script's object limit cuts it).
- **Hover a rule name** for a small picture of that rule built on its own ("Building a preview…" the first
  time; later hovers are instant).
- **Inline sliders** appear after `#define … (float:a-b)` and `#param` lines, mirrored in the Parameters dock.
- **Alt+drag** over a number scrubs it (Shift = fine, Ctrl = coarse).
- **Colours:** right-click a colour (`#f80`, `#FF8800`, `red`, also inside `#define` lines) and choose **Pick
  Colour…**; the script follows the picker live, **Cancel** restores it, and the change is one undo step. The
  new value keeps the literal's style (three-digit hex when possible, upper or lower case, a colour name when
  the choice is exactly one). Right-click elsewhere for **Insert Colour…**; **Ctrl+Shift+C** does either at the
  cursor, and **Ctrl+click** a colour also opens the picker.
- The **context menu** also has Go to Definition, Peek, Find References, Rename, Quick Fix, Refactor, Toggle
  Comment and Format Document.

## Refactoring

**Edit ▸ Refactor…** (Ctrl+Alt+R; the refactorings are also in the Ctrl+. menu) on a call or a rule:

- **Extract the transforms into a new rule:** `3 * { x 1 } box` becomes `newRule`, with `rule newRule { 3 * {
  x 1 } box }` added after the rule you are in.
- **Inline** a rule at one call, or — on the rule's `rule` line — everywhere, removing the rule. Only plain
  rules (one definition, no weight or maxdepth, no `set` lines, not recursive) can be inlined.
- **Convert `{ … } R` ↔ `1 * { … } R`**.

Each is one undo step and keeps the structure the script builds. Nothing is offered on a line that a
`#define` changes.

## Navigating

| Action | Shortcut |
|--------|----------|
| Go to Definition / Peek Definition | F12 / Alt+F12 |
| Find References | Shift+F12 |
| Rename Rule | F2 |
| Find / Replace / Find in Files | Ctrl+F / Ctrl+H / Ctrl+Shift+F |
| Quick Open (files, examples, `@rule`, `:line`) | Ctrl+P |
| Command Palette | Ctrl+Shift+P |
| Language Reference at the cursor | F1 |

The breadcrumb bar above the editor shows the rule you are in; the Outline dock lists every rule.

## Editing

- **Multiple cursors:** Alt+click adds a cursor; Ctrl+D adds the next occurrence of the word; Ctrl+Shift+L
  selects all occurrences; Ctrl+Alt+↑/↓ adds a cursor above/below; Alt+Shift+drag selects a column.
- **Folding:** rules, v2 blocks and comment runs fold from the gutter; Ctrl+Shift+[ / ] fold and unfold,
  Ctrl+K Ctrl+0 folds everything.
- **Comments:** Ctrl+/ toggles line comments, Shift+Alt+A block comments.
- **Format Document** (Shift+Alt+F) normalises spacing and indentation.
- **Split Editor** (Ctrl+\\) shows a second view of the same script.
- View toggles (**View ▸ Editor**): word wrap (Alt+Z), whitespace, indent guides, rainbow brackets, minimap,
  sticky scroll, breadcrumbs and **Vim keybindings**.

## Vim keybindings

Turn them on in **View ▸ Editor ▸ Vim Keybindings** (or Preferences ▸ Editor). The status bar shows the mode.

- Modes: normal, insert (`i a I A o O`, `s S C c…`), visual (`v`) and visual line (`V`); Escape returns to
  normal mode.
- Motions (with counts): `h j k l`, `w b e W B E`, `0 ^ $`, `gg G` (`5G` goes to line 5), `{ }`, `%`,
  `f t F T` with `; ,`.
- Operators with any motion: `d c y > <` (doubled for whole lines: `dd`, `cc`, `yy`, `>>`); in visual mode
  also `~`.
- Changes: `x X s S D C Y p P r J ~`, undo `u`, redo Ctrl+R, repeat `.`.
- `/text` searches (Enter), `n` / `N` repeat; `:w` saves, `:q` closes the tab, `:wq` / `:x` do both, `:12`
  goes to line 12.

Shortcuts with Ctrl keep working in every mode; completion and snippets work in insert mode.

## Files

- Sessions are restored: open tabs, unsaved changes and the window layout come back after a restart. After a
  crash, Structura offers the recovered text.
- Files changed on disk reload automatically when you have no unsaved changes.
- The status bar shows the file's encoding and line endings; Structura keeps them when saving (Structure
  Synth's Windows-1252 files stay Windows-1252).

## Themes and keys

- **View ▸ Choose Theme…** (Ctrl+K Ctrl+T): 40 themes, including six Nord variants, Dracula, Solarized,
  Gruvbox, Catppuccin, Tokyo Night and two high-contrast themes. The theme applies to the whole window.
- **View ▸ Edit Theme…** changes any colour with a live preview, checks contrast, and saves your own themes.
- **File ▸ Keyboard Shortcuts…** (Ctrl+K Ctrl+S): presets (Structura, Structure Synth 1.5, VS Code-like) and
  your own bindings; conflicts are marked.
- **File ▸ Preferences…** (Ctrl+,), in sections: General (sessions, recovery interval), Appearance (theme,
  follow the system's light/dark setting, interface font and size, density, reduced motion), Editor (code
  font, view options), Viewport (mouse controls: Structura, Structure Synth 1.5, Blender; engine), Rendering
  (device, default preset, CPU threads, memory guard), Paths (output folder, `#include` library folders,
  Blender), Advanced (log level, Reset Window Layout, Clear Caches).
