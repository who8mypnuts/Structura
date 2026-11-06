# The editor

## Writing

- **Completion** pops up as you type: rules, primitives, operators, settings, colours, v2 block keys and
  functions, and snippets. Tab or Enter accepts; snippet fields are visited with Tab.
- **Signature help** shows an operator's or function's arguments while you type them.
- **Hover** a word for its documentation; hover a rule call to highlight the objects it made in the viewport.
- **Diagnostics** underline errors and warnings as you type; the **Problems** dock lists them. **Ctrl+.**
  offers quick fixes (create a missing rule, fix a spelling, convert an alias …).
- **Inlay hints** show loop counts and the material a tag resolves to.
- **Inline sliders** appear after `#define … (float:a-b)` and `#param` lines, mirrored in the Parameters dock.
- **Alt+drag** over a number scrubs it (Shift = fine, Ctrl = coarse).
- **Ctrl+click** a colour to pick it with a colour dialog.

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
- View toggles (**View ▸**): word wrap (Alt+Z), whitespace, indent guides, rainbow brackets, minimap, sticky
  scroll.

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
- **File ▸ Preferences…** (Ctrl+,): fonts and sizes, editor options, language, viewport engine, render device.
