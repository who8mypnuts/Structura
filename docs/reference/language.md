# EisenScript language reference

Generated from the language catalogues (`tools/gen_reference.py`); do not edit by hand.

## Statements

The structure of a script.

| Name | Form | Description |
|---|---|---|
| `rule` | `rule NAME [maxdepth N [> OTHER]] [weight W] { … }` | Define a rule. Several definitions with the same name form an ambiguous rule: one is chosen at random, in proportion to the weights. maxdepth limits the recursion depth; '> OTHER' calls OTHER when the limit is reached. |
| `set` | `set KEY VALUE` | Change a build, view or render setting (see Settings). |
| `loop` | `N * { operators } RULE` | Apply the transformation N times, calling RULE after each step. '{ operators } RULE' is a single step; several loops can be chained. |
| `define` | `#define NAME VALUE [(float:A-B) \| (int:A-B)]` | Text substitution (v1: inside words too, W103). A range turns the define into a Parameters slider. |
| `version` | `#version 2` | First line: enable EisenScript v2 (blocks, #param, expressions, whole-word defines). |
| `param` | `#param NAME TYPE = VALUE [range A..B] ["Label"]` | (v2) A typed parameter with a slider. |
| `comment` | `// line, /* block */` | Comments. |

## Transformations

Inside '{ … }'. Transformations apply in the current (local) frame.

| Name | Form | Description |
|---|---|---|
| `x` | `x ‹float›` | Translate along the local x axis (post-multiplied, so in the current frame). |
| `y` | `y ‹float›` | Translate along the local y axis. |
| `z` | `z ‹float›` | Translate along the local z axis. |
| `rx` | `rx ‹degrees›` | Rotate about the x axis through the unit-cube centre line (y = z = 0.5). |
| `ry` | `ry ‹degrees›` | Rotate about the y axis through the unit-cube centre line (x = z = 0.5). |
| `rz` | `rz ‹degrees›` | Rotate about the z axis through the unit-cube centre line (x = y = 0.5). |
| `s` | `s ‹float› ‹float› ‹float›` | Scale about the unit-cube centre: one factor (uniform) or three (x y z). (also: size) |
| `matrix` | `matrix ‹float› ‹float› ‹float› ‹float› ‹float› ‹float› ‹float› ‹float› ‹float›` | Apply a 3×3 matrix (row-major) about the unit-cube centre. |
| `reflect` | `reflect ‹float› ‹float› ‹float›` | Reflect through the plane with normal (nx ny nz) that passes through the origin. |
| `fx` | `fx` | Mirror in x about the unit-cube centre (same as s -1 1 1). |
| `fy` | `fy` | Mirror in y about the unit-cube centre. |
| `fz` | `fz` | Mirror in z about the unit-cube centre. |
| `hue` | `hue ‹float›` | Add to the hue (degrees, wraps at 360). (also: h) |
| `sat` | `sat ‹float›` | Multiply the saturation (clamped to 0..1). |
| `brightness` | `brightness ‹float›` | Multiply the brightness/value (clamped to 0..1). (also: b, v) |
| `alpha` | `alpha ‹float›` | Multiply the opacity (clamped to 0..1). (also: a) |
| `color` | `color ‹color-or-random›` | Set an absolute colour (name, #rgb, #rrggbb, …) or 'random' to draw from the colour pool. (also: c) |
| `blend` | `blend ‹color› ‹float›` | Blend towards a colour in HSV space with the given strength. |
| `mat` | `mat ‹material›` | v2: the material inherited by the subtree (a declared 'material' block or a preset name); a tag (box::glass) overrides it. |

## Rule modifiers

After 'rule NAME'.

| Name | Form | Description |
|---|---|---|
| `weight` | `weight ‹float›` | Relative probability of this definition among rules with the same name. (also: w) |
| `maxdepth` | `maxdepth ‹int›` | Maximum recursion depth of this rule; optionally '> rule' names a retirement rule. (also: md) |

## Primitives

Built-in shapes; 'box::tag' selects a material or render class.

| Name | Form | Description |
|---|---|---|
| `box` | `box` | Solid unit cube [0,1]³. |
| `sphere` | `sphere` | Sphere centred in the unit cube; radius from the transformed z half-extent (always round). |
| `cylinder` | `cylinder` | Cylinder along the local x axis (v2). In Structure Synth 1.5 compatibility mode it draws nothing. |
| `mesh` | `mesh` | Quad tube swept from the parent's frame to the current frame. |
| `line` | `line` | Line from (0,.5,.5) to (1,.5,.5). |
| `dot` | `dot` | Point at the unit-cube centre. |
| `grid` | `grid` | Wireframe of the unit cube (12 edges). |
| `template` | `template` | Emits a template snippet (template::id) without geometry – used for CSG markers in templates. |
| `cone` | `cone[r]` | cone[r]: like cylinder, with the top radius r × the base radius (default 0: a point). |
| `torus` | `torus[r]` | torus[r]: ring in the local xy plane around the cube centre; major radius 0.5 − r/2, minor radius r/2. |
| `ellipsoid` | `ellipsoid` | The sphere inscribed in the unit cube, transformed like a box (non-uniform scale gives an ellipsoid). |
| `tube` | `tube[r]` | tube[r]: a line with a real thickness (diameter) r in object-space units, with rounded ends (default 0.1). |

## Settings

'set KEY VALUE' at the top level or inside a rule.

| Name | Form | Description |
|---|---|---|
| `maxdepth` | `set maxdepth ‹int›` | BFS: generation limit (default 1000). Depth-first: default per-rule depth limit. (also: md) |
| `maxobjects` | `set maxobjects ‹int›` | Maximum number of objects (default 100000). |
| `minsize` | `set minsize ‹float›` | Cull states whose transformed unit-diagonal is shorter than this. |
| `maxsize` | `set maxsize ‹float›` | Cull states whose transformed unit-diagonal is longer than this. |
| `seed` | `set seed ‹int\|initial›` | Reseed the random streams, or 'initial' to make a subtree replay the same random choices. |
| `background` | `set background ‹color›` | Background colour. |
| `colorpool` | `set colorpool ‹colorpool›` | Colour source for 'color random': randomhue, randomrgb, greyscale, image:FILE, list:C1,C2,… |
| `rng` | `set rng ‹old\|new›` | Obsolete: select the old C library random generator. |
| `syncrandom` | `set syncrandom ‹bool›` | All states in a generation share the same random draws. |
| `recursion` | `set recursion ‹depth›` | 'set recursion depth' switches to depth-first expansion. |
| `translation` | `set translation ‹vec3›` | Camera translation, e.g. [0 0 -20]. |
| `rotation` | `set rotation ‹mat3›` | Camera rotation as 9 numbers (row-major). |
| `pivot` | `set pivot ‹vec3›` | Camera pivot point. |
| `scale` | `set scale ‹float›` | Camera zoom. |
| `perspective-angle` | `set perspective-angle ‹float›` | Vertical field of view in degrees (default 22). |
| `opengl` | `set opengl ‹any›` | Ignored (accepted for compatibility). |
| `template` | `set template ‹any›` | Passed to template exporters. |

## Raytracer settings

'set raytracer::KEY value' (Structure Synth 1.5 renderer).

| Name | Form | Description |
|---|---|---|
| `samples` | `set raytracer::samples ‹int›` | Anti-aliasing grid: N×N samples per pixel. |
| `ambient-occlusion-samples` | `set raytracer::ambient-occlusion-samples ‹int›` | Ambient-occlusion grid: N×N rays per camera sample (0 turns AO off). |
| `max-depth` | `set raytracer::max-depth ‹int›` | Maximum ray depth (reflections and transparency). |
| `dof` | `set raytracer::dof ‹[center,falloff]›` | Depth of field: focal plane as a fraction between the near and far planes, and the blur strength. |
| `shadows` | `set raytracer::shadows ‹bool›` | Cast hard shadows from the point light. |
| `light` | `set raytracer::light ‹[x,y,z]›` | Point-light position (default: above and left of the camera). |
| `size` | `set raytracer::size ‹[WxH]›` | Output size; 0 on one axis keeps the window's aspect ratio. |
| `reflection` | `set raytracer::reflection ‹float›` | Mirror reflection of untagged primitives (0–1); 'raytracer::TAG::reflection' for one tag. |
| `phong` | `set raytracer::phong ‹[ambient,diffuse,specular]›` | Phong coefficients of untagged primitives (default 0.6, 0.6, 0.6); 'raytracer::TAG::phong' for one tag. |
| `progressive` | `set raytracer::progressive ‹bool›` | Accepted for compatibility (Structura always renders progressively). |
| `max-threads` | `set raytracer::max-threads ‹int›` | Accepted for compatibility (Structura schedules its own threads). |
| `voxel-steps` | `set raytracer::voxel-steps ‹int›` | Accepted for compatibility (Structura uses a BVH). |

## v2 blocks

Top-level blocks of EisenScript v2 ('#version 2').

| Name | Form | Description |
|---|---|---|
| `material` | `material { key value … }` | A named material: 'material NAME { … }', selected by tags (box::NAME) or the 'mat' state. |
| `material · preset` | `preset ‹name›` | Starting point: glass, mirror, metal, gold, chrome, matte, plastic, emissive, clay, ceramic. |
| `material · model` | `model ‹principled \| constant \| wireframe \| ao \| debug_normal \| debug_id \| debug_uv \| debug_generation \| debug_gray \| shadow_catcher›` | Shading model: principled (the default), flat constant colour, wireframe, ambient occlusion, a debug view, or shadow_catcher (shows the background, darkened by the shadows falling on it). |
| `material · base` | `base ‹state \| colour›` | Base colour; 'state' (the default) uses the structure's colour. |
| `material · metallic` | `metallic ‹0..1›` | Metalness. |
| `material · roughness` | `roughness ‹0..1›` | Microfacet roughness. |
| `material · specular` | `specular ‹0..1›` | Dielectric specular level (0.5 = IOR 1.5). |
| `material · ior` | `ior ‹number›` | Index of refraction. |
| `material · transmission` | `transmission ‹0..1›` | Glass-like transmission. |
| `material · transmission_roughness` | `transmission_roughness ‹0..1›` | Roughness of the transmitted lobe. |
| `material · emission` | `emission ‹colour strength›` | Emitted light: a colour and a strength. |
| `material · opacity` | `opacity ‹state \| 0..1›` | Alpha; 'state' (the default) uses the structure's alpha. |
| `material · coat` | `coat ‹0..1›` | Clear-coat layer weight. |
| `material · coat_roughness` | `coat_roughness ‹0..1›` | Clear-coat roughness. |
| `material · anisotropy` | `anisotropy ‹-1..1›` | Anisotropic stretch of the highlight. |
| `material · attenuation_color` | `attenuation_color ‹colour›` | Volume absorption colour of transmissive materials. |
| `material · attenuation_distance` | `attenuation_distance ‹number›` | Distance at which the absorption reaches the attenuation colour. |
| `material · thin_walled` | `thin_walled ‹bool›` | Treat transmissive surfaces as thin shells (no refraction offset). |
| `light` | `light { key value … }` | A named light: 'light NAME { type … }'. The first sun light also drives the sky. |
| `light · type` | `type ‹sun \| point \| sphere \| spot \| rect›` | Kind of light. rect: a one-sided rectangle facing its target (soft, area-sampled shadows). |
| `light · direction` | `direction ‹[x y z]›` | sun: the direction the light travels. |
| `light · intensity` | `intensity ‹number›` | sun: irradiance multiplier. |
| `light · angle` | `angle ‹degrees›` | sun: angular diameter (soft shadows). |
| `light · position` | `position ‹[x y z]›` | point, sphere, spot, rect: position (rect: its centre). |
| `light · radius` | `radius ‹number›` | sphere: radius of the emitting sphere. |
| `light · power` | `power ‹number›` | point, sphere, spot, rect: emitted power (comparable across types). |
| `light · target` | `target ‹[x y z]›` | spot, rect: the point the light faces. |
| `light · size` | `size ‹[w h]›` | rect: width and height of the rectangle. |
| `light · cone` | `cone ‹degrees›` | spot: half-angle of the cone. |
| `light · blend` | `blend ‹0..1›` | spot: fraction of the cone used for the soft edge. |
| `light · color` | `color ‹colour›` | Light colour. |
| `environment` | `environment { key value … }` | What camera rays and indirect light see when they miss the structure. |
| `environment · type` | `type ‹sunsky \| hdri \| color \| gradient›` | sunsky: the Preetham clear sky for the first sun light; hdri: an image (importance-sampled); color: uniform; gradient: top to bottom. |
| `environment · file` | `file ‹"path.exr"›` | hdri: an equirectangular .exr or .hdr image (relative to the script). |
| `environment · rotation` | `rotation ‹degrees›` | hdri, sunsky: turn the environment about the vertical axis. |
| `environment · intensity` | `intensity ‹number›` | hdri, sunsky: brightness multiplier. |
| `environment · turbidity` | `turbidity ‹1.7..10›` | sunsky: haze (2 = very clear, 3 = clear, 6+ = hazy). |
| `environment · ground` | `ground ‹colour›` | sunsky: the ground colour below the horizon. |
| `environment · color` | `color ‹colour›` | color: the uniform colour (#fff gives the white-studio look). |
| `environment · top` | `top ‹colour›` | gradient: zenith colour. |
| `environment · bottom` | `bottom ‹colour›` | gradient: nadir colour. |
| `camera` | `camera { key value … }` | The view; overrides the legacy 'set translation/rotation/pivot/scale' lines (W113). |
| `camera · type` | `type ‹perspective \| orthographic \| spherical \| fisheye›` | Projection. |
| `camera · position` | `position ‹[x y z]›` | Eye position. |
| `camera · target` | `target ‹[x y z]›` | Point looked at. |
| `camera · up` | `up ‹[x y z]›` | Up vector. |
| `camera · fov` | `fov ‹degrees›` | Vertical field of view (fisheye: across the image height). |
| `camera · height` | `height ‹number›` | orthographic: visible height in world units. |
| `camera · aperture` | `aperture ‹number›` | Lens radius for depth of field; 0 is a pinhole. |
| `camera · focus` | `focus ‹auto \| number›` | Focus distance; auto focuses on the target. |
| `camera · blades` | `blades ‹int›` | Aperture blades: 3 or more give polygonal bokeh (0: round). |
| `camera · blade_rotation` | `blade_rotation ‹degrees›` | Rotation of the aperture polygon (also written blade-rotation). |
| `render` | `render { key value … }` | Render settings; override 'set raytracer::…' lines (W113). |
| `render · integrator` | `integrator ‹path \| ao \| classic \| preview›` | path: physically based; ao: ambient occlusion; classic: Structure Synth 1.5's look; preview: fast. |
| `render · samples` | `samples ‹int›` | Samples per pixel. |
| `render · size` | `size ‹WxH›` | Output size in pixels, e.g. 1920x1080. |
| `render · filter` | `filter ‹box \| triangle \| gaussian \| blackman-harris \| mitchell \| catmull-rom \| bspline \| lanczos›` | Pixel reconstruction filter (importance-sampled; box is a plain jitter inside the pixel). |
| `render · max_bounces` | `max_bounces ‹int›` | Maximum path length (also written max-bounces). |
| `render · noise_threshold` | `noise_threshold ‹float›` | Adaptive sampling: a pixel stops once its relative noise is below this (e.g. 0.01; 0 = off). |
| `render · time_limit` | `time_limit ‹float›` | Stop rendering after this many seconds (0 = no limit). |
| `render · ground` | `ground ‹off \| plane \| catcher›` | A ground under the structure: a diffuse plane, or a shadow catcher that shows the background darkened by the shadows (path integrator). |
| `render · ground_color` | `ground_color ‹color›` | Colour of the ground plane. |
| `render · ground_offset` | `ground_offset ‹float›` | How far below the structure's lowest point the ground lies (world units). |
| `render · fog_density` | `fog_density ‹float›` | Fog: density per world unit at the fog base (0 = no fog). Rays fade towards the fog colour with distance. |
| `render · fog_falloff` | `fog_falloff ‹float›` | Fog: the height over which the density falls by a factor e (0 = even fog everywhere). |
| `render · fog_base` | `fog_base ‹float›` | Fog: the height of full density (default: the structure's lowest point). |
| `render · fog_color` | `fog_color ‹color›` | Fog: its colour. |
| `render · caustics` | `caustics ‹filtered \| on \| photons›` | Light focused by glass and mirrors: filtered (smooth, the default), on (unbiased, noisy) or photons (sharp sun caustics from a photon map). |
| `render · photon_count` | `photon_count ‹int›` | Caustic photons traced per render (caustics photons; default 300000). |
| `render · photon_radius` | `photon_radius ‹float›` | Photon gather radius in world units (0 = automatic: 0.6 % of the scene's size). |

## v2 expressions

'( expression )' wherever a number is expected. Angles are in degrees.

| Name | Form | Description |
|---|---|---|
| `sin` | `sin(degrees)` | Sine of an angle in degrees. |
| `cos` | `cos(degrees)` | Cosine of an angle in degrees. |
| `tan` | `tan(degrees)` | Tangent of an angle in degrees. |
| `asin` | `asin(x)` | Arc sine, in degrees. |
| `acos` | `acos(x)` | Arc cosine, in degrees. |
| `atan` | `atan(x)` | Arc tangent, in degrees. |
| `atan2` | `atan2(y, x)` | Angle of the vector (x, y), in degrees. |
| `sqrt` | `sqrt(x)` | Square root. |
| `pow` | `pow(base, exponent)` | base raised to exponent. |
| `exp` | `exp(x)` | e raised to x. |
| `log` | `log(x)` | Natural logarithm. |
| `abs` | `abs(x)` | Absolute value. |
| `min` | `min(a, b)` | The smaller value. |
| `max` | `max(a, b)` | The larger value. |
| `floor` | `floor(x)` | Largest integer ≤ x. |
| `ceil` | `ceil(x)` | Smallest integer ≥ x. |
| `round` | `round(x)` | Nearest integer. |
| `clamp` | `clamp(x, lo, hi)` | x limited to [lo, hi]. |
| `mix` | `mix(a, b, t)` | Linear interpolation a + (b − a)·t. |
| `pi` | `pi` | π ≈ 3.14159 |
| `tau` | `tau` | τ = 2π |
| `e` | `e` | Euler's number ≈ 2.71828 |

## Diagnostics

Problems reported while you type.

| Name | Form | Description |
|---|---|---|
| `E001` | `E001 · error` | Unexpected token. The parser expected something else here (Structure Synth 1.5 stops at the first error). |
| `E002` | `E002 · error` | Unterminated [ or /* or block. A '[', a '/*' comment or a v2 block is never closed. |
| `E003` | `E003 · error` | Unknown rule or primitive. A call names no rule, primitive, tagged primitive or triangle. |
| `E004` | `E004 · error` | Invalid number or fraction. A number could not be read (fractions are 'a/b'). |
| `E005` | `E005 · error` | Invalid colour. Colours are #rgb, #rrggbb, a colour name or 'random' (color only). |
| `E006` | `E006 · error` | Wrong argument for an operator. An operator is missing a numeric argument (for example 's' takes one or three numbers). |
| `E007` | `E007 · error` | Loop count must be an integer. 'N * { … }' needs a whole number N. |
| `E008` | `E008 · error` | maxdepth requires an integer. 'rule R maxdepth N' needs a whole number N. |
| `E009` | `E009 · error` | Invalid set command or build error. An unknown 'set' command, or a value the builder rejected. |
| `E010` | `E010 · error` | Redefinition of a primitive. A rule cannot be named like a primitive (box, sphere, …). |
| `E013` | `E013 · error` | Tag on a non-primitive. 'name::tag' is only allowed on primitives (box::shiny). |
| `E014` | `E014 · error` | Malformed triangle or primitive argument. triangle[x,y,z;x,y,z;x,y,z] needs three corners of three numbers; cone[r], torus[r] and tube[r] need one number. |
| `E016` | `E016 · error` | Expression error (v2). A '( expression )' uses an unknown name, divides by zero or is malformed. |
| `E017` | `E017 · error` | Invalid v2 block. A material, light, environment, camera or render block has an unknown key or a bad value. |
| `W101` | `W101 · warning` | Rule is never referenced. No call, retirement or top-level statement uses this rule. |
| `W102` | `W102 · warning` | Rule is unreachable. The rule is only called from rules that the top level never reaches. |
| `W103` | `W103 · warning` | #define replaces text inside other words (v1). Structure Synth 1.5 substitutes defines inside longer identifiers too; v2 substitutes whole words only. |
| `W104` | `W104 · warning` | Recursive #define. A define refers to itself; substitution stops after 100 rounds. |
| `W105` | `W105 · warning` | cylinder draws nothing in v1. Structure Synth 1.5 counts cylinders as objects but never draws them; '#version 2' draws them. |
| `W106` | `W106 · info` | Alias not valid in Structure Synth 1.5. 'size' and 'v' are accepted here but Structure Synth 1.5 rejects them. |
| `W108` | `W108 · info` | Recursion bounded only by the default maxdepth. A recursive rule has no maxdepth and the script sets no 'set maxdepth': the default (1000) applies. |
| `W109` | `W109 · warning` | 'set rng old' is obsolete. The Mersenne Twister is always used. |
| `W110` | `W110 · warning` | Ambiguous rule with total weight 0. Every alternative of this rule has weight 0, so none can be chosen fairly. |
| `W112` | `W112 · info` | Tag has no material (v2). No material block has this tag's name and it is not a built-in preset: the default material is used. |
| `W113` | `W113 · warning` | Legacy settings overridden by a v2 block. A camera or render block overrides the equivalent 'set' commands. |
| `W114` | `W114 · warning` | v2 syntax without '#version 2'. Blocks, #param and ( expressions ) need '#version 2' on the first line. |
| `W120` | `W120 · warning` | Unknown preprocessor command. A line starting with '#' is not #define, #param, #version or #javascript. |
| `W121` | `W121 · warning` | Malformed #define slider. A '#define NAME value (float:a-b)' slider could not be parsed. |
| `I204` | `I204 · info` | JavaScript script. A '#javascript' script drives the Builder API. It is not built live; run it with Build ▸ Run JavaScript (F7). |
| `I203` | `I203 · info` | Tag uses a built-in material preset (v2). The tag has no material block but matches a preset name (glass, mirror, gold …). |

