# 05 — EisenScript Language Specification

Structura supports two dialects:

| Dialect | Selected by | Guarantee |
|---------|-------------|-----------|
| **v1 (compat)** | Default for every file | Same structure as Structure Synth 1.5: objects, order, matrices (float32 tolerance), colours, RNG draws |
| **v2 (extended)** | The first non-blank line is `#version 2` | A strict superset at the *language* level, with better defaults (whole-word defines, working `cylinder`, expressions, materials, lights, camera) |

Structure Synth 1.5 reports `#version 2` only as a harmless "could not understand preprocessor command"
warning, so v2 files degrade gracefully when opened in the old tool.

The tables in this document are **data** in the codebase (`structura/core/lang/catalog/*.toml`). The parser,
completion engine, hover docs, lint messages and the generated language reference all read the same tables
(DRY).

---

## 1. Lexical structure (v1)

| Element | Rule |
|---------|------|
| Case | Keywords, operators, rule names and colours are **case-insensitive**. User strings are lower-cased. |
| Whitespace | Space, tab, CR, LF separate tokens. `{` and `}` are tokens and separators even without spaces. |
| Comments | `// …` to end of line; `/* … */` spanning lines; a line whose first character is `#` is removed by the tokenizer after preprocessing. |
| Bracket token | `[` … `]` is read as **one token**, including any spaces inside (e.g. `[0 0 -20]`, `triangle[0,0,0;1,0,0;0,1,0]`). An unterminated `[` is an error. |
| Number | A token starting with `+`, `-` or a digit. Integer (`12`), float (`0.95`, `1e-3`), or integer fraction `a/b` (float value a÷b). |
| Operators | `x y z rx ry rz s matrix hue h sat brightness b alpha a color c blend reflect fx fy fz maxdepth md weight w`, plus the aliases `size`→`s` and `v`→`brightness` (defects D2/D3 fixed in both modes) |
| Keywords | `rule`, `set` |
| Symbols | `{` `}` `*` `>` (`>` must be whitespace-separated) |
| User string | Any other token: rule names, primitive names with `::tag`, colours (`#f80`, `red`), set values |

## 2. Preprocessor (v1)

The preprocessor runs before tokenizing, line by line.

### 2.1 `#define`

```
#define NAME VALUE
```

- **v1 quirk (reproduced):** every later non-preprocessor line has *every substring* `NAME` replaced by
  `VALUE`. Keys are applied in **alphabetical order**. After each replacement the scan restarts from the
  first key, with at most 100 replacements per line. If `VALUE` contains `NAME`, the define is skipped with
  a warning. Lint `W103` lists identifiers that a define corrupts (for example, `#define s 2` corrupts `rule`).
- **v2:** whole-word replacement (`\bNAME\b`) in source order. `VALUE` may be an expression (§9.1).

### 2.2 GUI parameter defines

```
#define angle 20 (float:0-90)      // slider, float, default 20, range 0..90
#define n 6 (int:1-90)             // slider, integer
```

The parameter panel creates a control. Its current value is substituted exactly like a plain define.
v2 adds `#param` (§9.2).

### 2.3 `random[a,b]`

Each occurrence is replaced, line by line, by a uniform value in [a, b]. Values come from a dedicated MT19937
stream seeded with the build seed (same algorithm as the geometry stream, §7).

### 2.4 `#include "file.es"` (new in both modes; defect D4)

- Inserts the file's lines at this point. The path is resolved relative to the including file, then against
  the library paths (Preferences).
- Each file is included at most once, so there are no cycles (`E012` on a cycle).
- Line mapping is preserved, so diagnostics point into the included file.

> **As built (M11):** `core/lang/includes.py` expands includes before everything else (analysis, build, CLI).
> Paths resolve against the script's folder, then the library folders (Preferences ▸ Paths, separated by the
> system's path separator). Each file is included once; a file that is not found, or that includes itself, is
> an E012 error on the `#include` line. The editor's spans stay in the edited file: diagnostics, symbols and
> provenance that come from an included file point at the `#include` line that brought it in.

---

## 3. Grammar (v1, EBNF)

```ebnf
program        = { statement } EOF ;
statement      = rule_def | set_stmt | action ;

rule_def       = "rule" NAME { modifier } "{" { set_stmt | action } "}" ;
modifier       = ( "weight" | "w" ) NUMBER
               | ( "maxdepth" | "md" ) INTEGER [ ">" NAME ] ;

action         = transform_list NAME              (* one application *)
               | loop { loop } NAME               (* nested repetition *)
               | NAME ;                           (* plain call, state unchanged *)
loop           = INTEGER "*" transform_list ;
transform_list = "{" { transform } "}" ;

transform      = ( "x" | "y" | "z" ) NUMBER
               | ( "rx" | "ry" | "rz" ) NUMBER          (* degrees *)
               | ( "s" | "size" ) NUMBER [ NUMBER NUMBER ]
               | "matrix" NUMBER NUMBER NUMBER NUMBER NUMBER NUMBER NUMBER NUMBER NUMBER
               | ( "hue" | "h" ) NUMBER
               | "sat" NUMBER
               | ( "brightness" | "b" | "v" ) NUMBER
               | ( "alpha" | "a" ) NUMBER
               | ( "color" | "c" ) COLOR_OR_RANDOM
               | "blend" COLOR NUMBER
               | "reflect" NUMBER NUMBER NUMBER
               | "fx" | "fy" | "fz" ;

set_stmt       = "set" SET_KEY VALUE_TOKEN ;      (* value is a single token; see §6 *)
NAME           = USER_STRING ;                    (* rule | primitive[::tag] | triangle[...][::tag] | template::id *)
```

The top-level statements form an implicit rule, **TopLevelRule**, which is applied first (generation 0).

---

## 4. Semantics

### 4.1 State

| Field | Initial value | Notes |
|-------|---------------|-------|
| `M` | identity 4×4 | Object-to-world affine transform of the unit cube [0,1]³ |
| `hsv` | (0°, 1, 1) — red | Hue in degrees [0,360); saturation and value in [0,1] |
| `alpha` | 1 | |
| `depth[rule]` | empty map | Remaining recursion budget per rule that has a depth limit |
| `prev` | none | Parent's (M, hsv, alpha), recorded by actions with transforms; used by `mesh` |
| `seed` | 0 | Non-zero after `set seed initial` (§7, item 3) |

### 4.2 Transformations

All geometric operators **post-multiply** (`M ← M · T`), so they act in the current local frame. Rotations,
scales and `matrix` pivot on the unit-cube centre.

| Op | T |
|----|---|
| `x d`, `y d`, `z d` | Translation along the local axis |
| `rx a` | `Tr(0,.5,.5) · Rx(a) · Tr(0,−.5,−.5)` (a in degrees; the legacy code uses π ≈ 3.14159265) |
| `ry a` | `Tr(.5,0,.5) · Ry(a) · Tr(−.5,0,−.5)` |
| `rz a` | `Tr(.5,.5,0) · Rz(a) · Tr(−.5,−.5,0)` |
| `s k` / `s kx ky kz` | `Tr(.5,.5,.5) · diag(kx,ky,kz) · Tr(−.5,−.5,−.5)` |
| `matrix m0..m8` | `Tr(.5,.5,.5) · [[m0 m1 m2][m3 m4 m5][m6 m7 m8]] · Tr(−.5,−.5,−.5)` |
| `reflect nx ny nz` | Plane reflection through the origin with normal n (no centre pivot) |
| `fx`, `fy`, `fz` | `s −1 1 1`, `s 1 −1 1`, `s 1 1 −1` (centre pivot) |

A transform list composes its operators left to right into a single transformation: the matrix product plus
a combined colour operation (§4.3).

### 4.3 Colour operations

| Op | Effect on state |
|----|-----------------|
| `hue d` | `h ← wrap360(h + d)` |
| `sat k` | `s ← clamp01(s·k)` |
| `brightness k` | `v ← clamp01(v·k)` |
| `alpha k` | `α ← clamp01(α·k)` |
| `color C` | Absolute: `(h,s,v,α) ← QColor(C).toHsv()`, with **8-bit quantised** s, v, α and **h = −1 for achromatic colours** (reproduced) |
| `color random` | Absolute colour drawn from the colour pool (§6.2), using the *colour* RNG stream |
| `blend C k` | `hsv ← (hsv + k·hsv(C)) / (1 + k)`, then hue wrapped and s, v clamped (HSV-space blend, as in 1.5) |

When one list combines several colour operators, relative operators accumulate (Δh adds, factors multiply).
If two absolute colours appear, the last one wins. The final RGB is `HSVtoRGB(h, s, v)` (legacy function,
sector `floor(h/60) mod 6`), interpreted as **sRGB**.

### 4.4 Actions and loops

- `NAME`: the child state is an exact copy of the parent's.
- `{T} NAME`: a loop with count 1. The child gets `prev = parent`, then `T` is applied once.
- `n1 * {T1} n2 * {T2} … NAME`: odometer iteration with **counters starting at 1**. The first loop is the
  fastest. For each combination `(c1, c2, …)` the child state is `parent · T1^c1 · T2^c2 · …`, with colour
  operations applied the same number of times. Example: `3 * { x 1 } R` produces R at x = 1, 2, 3.
- Each emitted child is appended to the next generation in emission order.

### 4.5 Rules

- **Custom rule:** `rule NAME [modifiers] { actions }`. Applying it applies every action in order.
- **Ambiguous rule:** several definitions with the same name. On application, `r = W·U[0,1]` is drawn from
  the *geometry* stream, where W is the sum of weights. The first definition with `r ≤ cumulative weight`
  is applied. The default weight is 1.
- **Depth limit** `maxdepth N [> R2]`:
  - On first application, `depth[rule] = N−1`.
  - On later applications, the budget is decremented.
  - At 0 the rule is *retired*. Without a retirement rule, nothing happens. With one, `depth[rule] ← N` is
    reset and R2 is applied in place.
  - Actions emitted by a depth-limited rule carry the new budget in their child states.
- **Primitives** (built-in rules; a name collision with a user rule is error `E010`):

| Primitive | Geometry (object space → world via M) | v1 | v2 |
|-----------|----------------------------------------|----|----|
| `box` | Unit cube [0,1]³ | ✓ | ✓ |
| `sphere` | Centre M·(.5,.5,.5), radius ‖M·(.5,.5,.5) − M·(.5,.5,0)‖. Always round. | ✓ | ✓ |
| `grid` | The 12 edges of the unit cube (wireframe) | ✓ | ✓ |
| `line` | Segment M·(0,.5,.5) → M·(1,.5,.5) | ✓ | ✓ |
| `dot` | Point M·(.5,.5,.5) | ✓ | ✓ |
| `mesh` | Quad tube from `prev.M` to `M`, cross-section (0,0)–(1,0)–(1,1)–(0,1) in xy; colours interpolate from `prev` to current | ✓ | ✓ |
| `triangle[x,y,z;x,y,z;x,y,z]` | Object-space triangle | ✓ | ✓ |
| `cylinder` | **v1: emits nothing** (D1, lint `W105`) | ∅ | Axis M·(0,.5,.5) → M·(1,.5,.5), elliptical cross-section inscribed in the cube face |
| `template::ID` | No geometry. Emits the template snippet `template::ID` in order (used for CSG begin/end) | ✓ | ✓ |
| `cone[r]`, `torus[r]`, `ellipsoid`, `tube[r]` | — | — | §9.6 |

- **Tags:** `prim::tag` assigns a class tag, which selects the material (§9.3) and legacy per-tag raytracer
  settings. Triangles support tags in both modes (D6 fixed).

---

## 5. Build algorithm

### 5.1 Breadth-first (default)

```text
stack = [(TopLevelRule, initial_state)]; generation = 0; objects = 0
while stack and generation < maxdepth and objects < maxobjects and len(stack) < maxobjects:
    next = []
    sync = geometry.getInt()        # ALWAYS drawn once per generation (even without syncrandom) — affects RNG order
    for (rule, state) in stack:
        if state.seed != 0: reseed_both_streams(state.seed); state.seed = geometry.getInt()
        if syncrandom: reseed_both_streams(sync)
        if size_culled(state): continue                     # minsize / maxsize
        rule.apply(state) → appends children to `next`, emits primitives
    stack = next; generation += 1
```

### 5.2 Depth-first (`set recursion depth`)

- Pending states form a list. The head is applied, and its children are inserted *in order* at the front.
- The global `maxdepth` becomes the default depth limit of every rule without its own limit.
- The only termination condition is `objects < maxobjects`.
- `syncrandom` has no effect, and there is no per-generation draw.
- 1.5 hangs when a state is size-culled in DFS mode, because the culled head is never removed (D15).
  Structura removes the culled state, which is the only sensible reading.

### 5.3 Termination reporting

The build reports each termination cause, as 1.5 did: object cap, pending-state cap, generation cap,
min/max-size culls, or user cancel. They appear as structured stats in the Console and Build panel.

---

## 6. `set` commands

Values are single tokens. Square brackets are stripped where a vector is expected.

### 6.1 Builder and scene

| Key | Value | Effect |
|-----|-------|--------|
| `maxdepth` / `md` | int | BFS: generation limit. DFS: default per-rule limit. Default 1000. |
| `maxobjects` | int | Object cap (default **100,000**) |
| `minsize`, `maxsize` | float | Size culling thresholds (0 = off) |
| `seed` | int \| `initial` | int: reseed both streams now (the UI seed box adopts it). `initial`: store the initial seed in the state (§7, item 3). |
| `background` | colour | Background colour |
| `colorpool` | `randomhue` \| `randomrgb` \| `greyscale`/`grayscale` \| `image:PATH` \| `list:C1,C2,…` | Source for `color random` |
| `rng` | `old` \| `new` | `old` (C `rand`) was platform-dependent. Structura keeps MT and emits `W109`. |
| `syncrandom` | `true` \| `false` | All states in a generation share random draws |
| `recursion` | `depth` | Depth-first traversal (detected at parse time) |
| `translation`, `pivot` | `[x y z]` | Camera (see §8) |
| `rotation` | `[9 numbers]` | Camera rotation, row-major |
| `scale` | float | Camera zoom |
| `perspective-angle` | float | Vertical FOV in degrees (default 22) |
| `opengl`, `template` | any | Accepted and passed through (no effect on the build) |

### 6.2 Colour pool draws

| Pool | Draw (colour stream) |
|------|----------------------|
| `randomhue` | `hsv(getInt(359), 255, 255)` |
| `greyscale` | `r=getInt(255)` → grey |
| `randomrgb` | three `getInt(255)` draws: r, g, b |
| `image:P` | `x=getInt(w−1)`, `y=getInt(h−1)` → pixel colour |
| `list:…` | `getInt(n−1)` → list entry |

### 6.3 Legacy raytracer settings → render settings

| Key | Maps to ([10](10-renderer-shading.md) §6) |
|-----|--------------------------------------------|
| `raytracer::samples N` | `classic.aa_grid = N` (N×N samples) |
| `raytracer::ambient-occlusion-samples N` | `classic.ao_grid = N` |
| `raytracer::max-depth N` | `max_bounces = N` |
| `raytracer::dof [center,falloff]` | Thin lens derived from the legacy parameters |
| `raytracer::shadows B` | `classic.shadows` |
| `raytracer::light [x,y,z]` | Point light position (legacy default: derived from the camera) |
| `raytracer::size [WxH]` | Output size (0 on one axis = keep the window aspect ratio) |
| `raytracer::progressive B`, `max-threads N`, `voxel-steps N` | Accepted; mapped to scheduler hints or ignored with an info diagnostic |
| `raytracer::reflection k`, `raytracer::phong [a,d,s]` | Default material: `legacy_reflection`, `legacy_phong` |
| `raytracer::TAG::reflection k`, `raytracer::TAG::phong […]` | The same, for material TAG |

---

## 7. Randomness

1. **Streams.** There are two MT19937 generators, *geometry* and *colour*, both seeded with the build seed.
   A third preprocessor stream serves `random[a,b]`.
2. **Primitives.**
   - `getDouble() = randInt() / 4294967295.0`.
   - `getInt(n)` masks to the smallest all-ones bit mask ≥ n and rejects draws above n.
   - `getInt()` is the raw 32-bit value.
   - Seeding uses standard `init_genrand(seed mod 2³²)`.
3. **`set seed initial`.** On first use it draws `initialSeed` from the geometry stream (once per build). It
   stores that seed in the state. Every rule application on a seeded state reseeds both streams from the
   stored seed, then replaces the stored seed with `geometry.getInt()`. Sibling subtrees therefore replay
   identically.
4. **UI seed.** Build with seed S. "Auto-increment" adds 1 (mod 32768) before each build, as in 1.5.

---

## 8. Camera semantics (v1)

```
view = Translate(translation) · Scale(scale) · Rotation3x3(rotation) · Translate(−pivot)
projection = perspective(fovy = perspective-angle, aspect = viewport, near = 5, far = 60)
```

Structura converts this to a physical camera (eye, target, up, fov, ortho-equivalent scale) on import. It
converts back when writing "Copy camera to script" in v1 format ([08](08-viewport.md) §7). The near and far
planes are legacy viewport details. The renderer does not use them.

---

## 9. v2 extensions

All of the following require `#version 2`. v2 also enables:

- whole-word defines;
- context-sensitive lexing, so operator names can be rule names (D8);
- a working `cylinder`.

### 9.1 Compile-time expressions

Anywhere a NUMBER is expected, `( expr )` may appear:

```
#version 2
#define twist 12
rule R md 40 { { rz (twist * 0.5) s (1 - 1/40) x (sin(pi/6)) } R  box }
```

| Category | Items |
|----------|-------|
| Operators | `+ - * / % ^`, unary `-`, parentheses |
| Functions | `sin cos tan asin acos atan atan2 sqrt pow exp log abs min max clamp floor ceil round mix` (trig functions take **degrees**, consistent with `rx`) |
| Constants | `pi tau e` |
| Random | `rand(a, b)`: compile-time, from the preprocessor stream, equivalent to `random[a,b]` |
| Animation | `time`, `frame`, `fps` (bound per frame by the timeline; [16](16-animation-scripting-cli.md)) |
| Parameters | Names from `#define` and `#param` |

Expressions are evaluated **once at compile time**, not per state. Per-state expressions (for example
`depth`) are a post-1.0 idea.

### 9.2 Typed parameters

```
#param angle  float = 20    range 0..90  "Branch angle"
#param n      int   = 6     range 1..90
#param tint   color = #f80
#param caps   bool  = true
#param style  enum  = spiral  of spiral|grid|tree
```

Parameters appear in the Parameters panel, can be keyframed ([16](16-animation-scripting-cli.md)), are type
checked (`E015` on a type mismatch at the use site), and can be used in expressions.

> **As built (M11):** float and int parameters are sliders (and keyframable); `color` is a colour button that
> substitutes `#rrggbb`; `bool` a switch that substitutes `1` / `0` (for expressions); `enum` a choice list
> that substitutes the chosen name — typically a rule, so `style` above calls `spiral`, `grid` or `tree` (the
> choices count as references for the unused-rule warnings). E015 reports a default that does not fit its
> type or range, and a colour used where a number is needed (or the other way round).

### 9.3 Materials

```
material shiny {
  preset    plastic          # optional starting point (see doc 10, §3.3)
  base      state            # 'state' (default) or a colour
  metallic  0.0
  roughness 0.15
  specular  0.5
  ior       1.5
  transmission 0.0
  emission  #ffffff 0.0      # colour, strength
  opacity   state            # state alpha (default) or a number
}
box::shiny                   # selects the material through the tag
{ mat shiny } R              # v2 state operator: inherited material for the subtree (a tag overrides it)
```

- A tag with no declared material and the same name as a built-in preset (`glass`, `mirror`, `metal`, `gold`,
  `chrome`, `matte`, `plastic`, `emissive`, `clay`, `ceramic`) uses that preset, with info diagnostic `I203`.
- In both modes, legacy `set raytracer::TAG::…` values are applied on top.

### 9.4 Lights & environment

```
light key  { type sun    direction [-1 -2 -1]  color #fff  intensity 3  angle 0.53 }
light fill { type sphere position  [0 10 0]    radius 1    color #ffe  power 200 }
light spot { type spot   position  [5 5 5]     target [0 0 0]  cone 30  blend 0.2  power 150 }
environment { type sunsky  sun key  turbidity 3  ground #333 }
# or: environment { type hdri  file "studio.exr"  rotation 90  intensity 1 }
# or: environment { type color #ffffff }      # the Sunflow-AO "white studio" look
# or: environment { type gradient  top #9bd  bottom #fff }
```

### 9.5 Camera & render blocks

```
camera {
  type perspective          # perspective | orthographic | spherical | fisheye
  position [0 0 20]  target [0 0 0]  up [0 1 0]
  fov 35                    # vertical, degrees (ortho: 'height' instead)
  aperture 0.05             # lens radius; 0 = pinhole
  focus auto                # auto (target distance) | number
  blades 6  blade-rotation 0
}
render {
  integrator path           # path | ao | classic | preview
  samples 512  size 1920x1080  max-bounces 8
  filter mitchell  denoise true  view agx  exposure 0
}
```

When both are present, `camera`/`render` blocks override the legacy `set` equivalents, with warning `W113`.

### 9.6 Additional primitives

| Primitive | Definition (unit-cube conventions) |
|-----------|-------------------------------------|
| `cylinder` | Capped; axis x from (0,.5,.5) to (1,.5,.5); radius 0.5 in y and z before transformation |
| `cone[r]` | Like `cylinder`, with top radius = r·base radius (default r = 0) |
| `torus[r]` | In the local xy plane, centred at (.5,.5,.5); major radius 0.5−r/2, minor radius r/2 (default r = 0.2) |
| `ellipsoid` | The sphere inscribed in the unit cube, transformed by M (non-uniform scale respected) |
| `tube[r]` | `line` with a real thickness (diameter) r in object-space units, with rounded ends (default r = 0.1) |

Bracket arguments follow the existing `triangle[...]` syntax, so the v1 tokenizer rules stay unchanged.

---

## 10. Diagnostics catalogue

Codes are stable. Messages live in `catalog/diagnostics.toml`, and this table is generated from it.

<!-- diagnostics:begin (generated by tools/gen_reference.py) -->
| Code | Severity | Meaning |
|------|----------|---------|
| E001 | error | Unexpected token |
| E002 | error | Unterminated [ or /* or block |
| E003 | error | Unknown rule or primitive |
| E004 | error | Invalid number or fraction |
| E005 | error | Invalid colour |
| E006 | error | Wrong argument for an operator |
| E007 | error | Loop count must be an integer |
| E008 | error | maxdepth requires an integer |
| E009 | error | Invalid set command or build error |
| E010 | error | Redefinition of a primitive |
| E012 | error | Include error |
| E013 | error | Tag on a non-primitive |
| E014 | error | Malformed triangle or primitive argument |
| E015 | error | Parameter type mismatch (v2) |
| E016 | error | Expression error (v2) |
| E017 | error | Invalid v2 block |
| W101 | warning | Rule is never referenced |
| W102 | warning | Rule is unreachable |
| W103 | warning | #define replaces text inside other words (v1) |
| W104 | warning | Recursive #define |
| W105 | warning | cylinder draws nothing in v1 |
| W106 | info | Alias not valid in Structure Synth 1.5 |
| W108 | info | Recursion bounded only by the default maxdepth |
| W109 | warning | 'set rng old' is obsolete |
| W110 | warning | Ambiguous rule with total weight 0 |
| W112 | info | Tag has no material (v2) |
| W113 | warning | Legacy settings overridden by a v2 block |
| W114 | warning | v2 syntax without '#version 2' |
| W120 | warning | Unknown preprocessor command |
| W121 | warning | Malformed #define slider |
| I204 | info | JavaScript script |
| I203 | info | Tag uses a built-in material preset (v2) |
<!-- diagnostics:end -->

Codes planned earlier but not reported yet:

- **E011** (retirement cycle): deliberately allowed. Structure Synth 1.5 accepts `A > B` with `B > A`, and such
  scripts build.
- **W107** (object estimate): shown as an inlay hint after each top-level call (`core/lang/estimate.py`)
  rather than a diagnostic.
- **W111** (build cap): not reported yet; the Build Stats panel shows the cap instead.
- **I201** (rule probabilities): shown as inlay hints rather than a diagnostic.

---

## 11. Compatibility notes verified against the original engine

The golden harness ([18](18-testing-and-quality.md) §3) runs the original Structure Synth 1.5 code. These
behaviours were **observed there** and are reproduced in v1 mode. Some correct or refine statements
elsewhere in this document.

| # | Behaviour | Where |
|---|-----------|-------|
| C1 | A loop count ≤ 0 behaves like 1. The loop body runs before the count is checked, like a do-while. | §4.4 |
| C2 | Tabs are **not** token separators. All whitespace inside a token is deleted, so `x<TAB>1` becomes the token `x1`. | §1 |
| C3 | Only CR ends a `//` line comment. `/*` starts a block comment even inside a line comment. `*/` is consumed anywhere. | §1 |
| C4 | A recursive `#define` is reported as "skipped" but **is still applied**, until the 100-substitution cap. | §2.1 |
| C5 | Identical `random[a,b]` texts on one line are replaced by **one** shared value. | §2.3 |
| C6 | GUI parameters: float values are rounded to **2 decimals**, then clamped. Values are substituted over the **whole** preprocessed document (including `#` lines), alphabetically, with one shared cap of 100. | §2.2 |
| C7 | A trailing comment after `(float:a-b)` turns the line into a *plain* define whose value includes the comment text. (1.5's own snippet menu inserts such lines.) | §2.2 |
| C8 | Termination is checked once per BFS generation, so a generation can **overshoot** `maxobjects`. | §5.1 |
| C9 | Depth-first mode: all listed rules get `maxdepth 1000` before the script runs. A script's `set maxdepth N` therefore only reaches rules whose depth is still ≤ 0, which in practice means the alternatives of ambiguous rules (these are always overwritten). | §5.2 |
| C10 | `cylinder`, and `mesh` without a previous state, **count as objects** but draw nothing. | §4.5 |
| C11 | Emitted direction vectors are computed as `M·e − M·0` in float32 (for example 0.99999994), not read from the matrix. | §4.2 |
| C12 | `QColor::toHsv` works in double precision, and saturation/value/alpha are rounded 16→8-bit divisions by 257 (Qt 6 differs). | §4.3 |
| C13 | `set` values are validated **when executed**. A bad value in a rule that never runs is not an error. | §6 |
| C14 | `triangle[…]::tag` fails in 1.5: the tokenizer splits `::tag` off after the bracket. v1 keeps this; tagged triangles are a v2 feature (this corrects D6 in [01](01-legacy-analysis.md)). | §4.5 |
| C15 | Retirement cycles (`A > B`, `B > A`) terminate, because a retirement resets the depth. Structura bounds a retirement chain at 100,000 steps as a safety net (this corrects D7). | §4.5 |
