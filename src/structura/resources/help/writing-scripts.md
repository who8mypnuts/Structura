# Writing scripts

EisenScript describes a structure as **rules** that call each other with **transformations**. The full
reference is in [reference/language.md](language.md); this page is the short tour.

## Rules and primitives

```
R1                                  // start: call rule R1
rule R1 { { x 1 rz 10 } R1 box }    // R1 draws a box and calls itself, moved and turned
```

- Primitives: `box`, `sphere`, `dot`, `line`, `grid`, `mesh`, `cylinder` (v2), `triangle[x,y,z;x,y,z;x,y,z]`.
- `box::glass` adds a **tag**: it selects a material (v2) or a render class (1.5's `set raytracer::glass::…`).
- Recursion ends at `set maxdepth N` or `set maxobjects N`, or with a rule modifier: `rule R md 20 { … }`.
- Several rules with one name are chosen at random, by weight: `rule R w 2 { … }`.

## Transformations

Inside `{ }`, applied left to right in the current frame:

| Operator | Meaning |
|----------|---------|
| `x y z` | move along the local axis |
| `rx ry rz` | rotate (degrees) about the axis through the unit-cube centre |
| `s f` / `s fx fy fz` | scale about the centre |
| `fx fy fz` | mirror |
| `matrix m0 … m8` | any 3×3 matrix |
| `hue h`, `sat f`, `b f`, `a f` | colour and opacity (HSV) |
| `color c` / `color random` | absolute colour (`#f80`, `red`, …) or from the colour pool |
| `blend c f` | move the colour towards `c` |

`12 * { rz 30 } R` repeats: twelve calls, each turned another 30°.

## Settings

`set background #223`, `set seed 7`, `set colorpool randomhue`, `set maxdepth 100`, `set recursion depth`,
and the camera lines Structure Synth writes (`set translation`, `set rotation`, `set scale`, `set pivot`).

## Parameters

`#define SIZE 0.9 (float:0.5-1.2)` declares a **slider** in the Parameters dock and in the editor. Every use of
`SIZE` takes its value. Plain `#define NAME TEXT` substitutes text.

While you drag a slider the structure is rebuilt with at most 250,000 objects, so it follows the slider; the
full build comes when you let go. Undoing a change, or going back to a value you had, shows the earlier
structure at once.

## Includes

`#include "library.es"` inserts that file's lines (rules, defines) at this point. The file is looked for next
to the script, then in the library folders of Preferences ▸ Paths. Each file is included once. Errors in an
included file are shown on the `#include` line.

## Build limits

**Build ▸ Build Limits…** caps every build: an object limit, a time limit, and a memory guard (the share of
the free memory a build may use). A build that reaches a limit stops and keeps what it made; the status bar
says which limit stopped it.

## EisenScript v2

Start a script with `#version 2` to get the additions (every 1.5 script keeps working without it):

- **Expressions** wherever a number goes: `{ rz (360 / n) s (0.9 ^ 2) } R`. They can read `frame`, `time`
  and `fps` for animation.
- **`#param n int = 12 range 3..40 "Arms"`** declares a typed slider. Other types get their own controls:
  `#param tint color = #f80` (a colour button), `#param caps bool = true` (a switch, `1` or `0` in
  expressions) and `#param style enum = tree of spiral|grid|tree` (a choice list — the name is substituted, so
  it can pick which rule to call).
- **Blocks:** `material NAME { … }`, `light NAME { … }`, `environment { … }`, `camera { … }`, `render { … }`.
- **`{ mat gold } R`** gives a whole subtree a material (a tag on a primitive still wins).
- **Primitives:** `cylinder`, `cone[r]`, `torus[r]`, `ellipsoid`, `tube[r]`.
- `#define` replaces whole words only (1.5 also replaced inside words: `#define R 3` turned `R1` into `31`).

```
#version 2
#param arms int = 8 range 3..24
material shiny { preset gold roughness 0.2 }
light key { type sun direction [-1 -2 -1] intensity 3 }
environment { type sunsky turbidity 3 }
render { ground catcher }

arms * { ry (360 / arms) } { mat shiny } Arm
rule Arm md 30 { { y 0.9 rz 8 s 0.95 } Arm cone[0.6] }
```

**Edit ▸ Convert to EisenScript v2** (or `structura convert`) migrates a 1.5 script so that it builds the
same structure.

## JavaScript movie scripts

Structure Synth's `#javascript` scripts run with **Build ▸ Run JavaScript** (F7) or `structura run`. The
`Builder` object has 1.5's API (`load`, `define`, `build`, `raytraceToFile`, `execute`, …); `Debug` (`Info`,
`Message`, progress, `Sleep`, `waitForMouseButton` — click in the viewport), `World` (`addSphere`, `setColor`,
`clear`) and `Vector3` are there too. Scripts run in their own process: the window never waits for them, each
`Builder.build()` shows its structure in the viewport, **Cancel** stops the script, and `Builder.execute` asks
before it runs a program.

**File ▸ Save as Legacy .es…** writes a copy Structure Synth 1.5 can open: v2 features are flattened (sliders
become 1.5 sliders, expressions their values, the camera block `set` lines) or dropped, and the Console lists
what changed.
