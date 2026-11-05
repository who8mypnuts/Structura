# 07 — Scene Model (`structura.core.scene`)

`SceneIR` is the **single contract** between the builder and every consumer: viewport, both renderer
backends, all exporters, and statistics. Structure Synth used three visitor classes that each re-derived
geometry (`OpenGLRenderer`, `TemplateRenderer`, `ObjRenderer`). Structura produces the data once and every
consumer reads it.

## 1. Design rules

1. **Struct-of-arrays** numpy arrays: contiguous, vectorisable, zero-copy into GPU buffers and Numba.
2. **Immutable** after the build. Arrays are set read-only, and the dataclasses are frozen.
3. **Instances, not meshes.** A primitive is a *kind* plus an affine transform of a unit shape. Tessellation
   happens lazily, and only for consumers that need triangles ([15](15-export.md) §2).
4. **Emission order is preserved** (row order = build order). Template export and `template::*` markers need it.
5. **Authored colours are stored as authored (sRGB, 0–1).** Conversion to linear happens in exactly one
   place: the render/viewport packers.

## 2. `SceneIR`

```python
@dataclass(frozen=True)
class SceneIR:
    id: SceneId                      # content hash: program hash + seed + limits
    instances: InstanceTable         # all primitives, emission order
    meshes: MeshSweepTable           # extra data for `mesh` primitives
    triangles: TriangleTable         # object-space triangles for `triangle[...]`
    template_calls: TemplateCallTable# `template::ID` markers (no geometry)
    tags: tuple[str, ...]            # index 0 = "" (untagged)
    materials: MaterialLibrary       # resolved per tag (+ v2 declared, presets, legacy overrides)
    lights: tuple[Light, ...]
    environment: Environment
    camera: Camera                   # from script (legacy set / v2 block) — may be overridden by project
    background: RGB                  # sRGB authored
    render_settings: RenderSettings  # from script; merged with project overrides downstream
    bounds: AABB                     # world bounds of all geometry
    stats: BuildStats
    provenance: ProvenanceIndex      # action id → source span (file, line, col)
```

### 2.1 `InstanceTable` (N rows)

| Column | dtype / shape | Meaning |
|--------|---------------|---------|
| `kind` | `u1` (N) | `PrimitiveKind` |
| `xform` | `f4` (N, 3, 4) | Object→world affine; columns = images of e_x, e_y, e_z, plus the origin (`dir1, dir2, dir3, base` in legacy terms) |
| `rgba` | `f4` (N, 4) | Authored sRGB colour + alpha |
| `tag` | `u2` (N) | Index into `tags` |
| `material` | `u2` (N) | Resolved material id (tag > v2 `mat` state > default) |
| `source` | `u4` (N) | Call-site action id (provenance) |
| `generation` | `u2` (N) | Build generation (BFS) or depth (DFS) |
| `aux` | `i4` (N) | Row in `meshes` / `triangles` / `template_calls`; −1 if unused |

Memory is 79 bytes per instance, for about 79 MB at 1M instances. The `xform` is stored as 3×4 because the
last row is always (0,0,0,1) for emitted primitives.

### 2.2 `PrimitiveKind`

| Value | Kind | Unit shape (object space) | Render representation | Export tessellation |
|-------|------|---------------------------|-----------------------|---------------------|
| 0 | `BOX` | [0,1]³ | Analytic box (slab test in object space) | 12 triangles (8 verts shared, or 24 for flat normals) |
| 1 | `SPHERE` | Round sphere; centre and radius derived (see [05](05-eisenscript-language.md) §4.5) | Analytic sphere (world space) | UV sphere or icosphere, LOD presets |
| 2 | `ELLIPSOID` (v2) | Inscribed sphere under M | Analytic (object-space sphere) | Same, transformed |
| 3 | `CYLINDER` (v2) | Axis x, radius 0.5 | Analytic capped cylinder (object space) | n-gon prism + caps |
| 4 | `CONE` (v2) | Axis x, top ratio in `aux` param | Analytic cone | n-gon frustum |
| 5 | `TORUS` (v2) | xy plane, minor ratio param | Triangle BLAS (shared unit torus, instanced) | Shared unit torus |
| 6 | `LINE` | (0,.5,.5)→(1,.5,.5) | Thin capsule with a configurable screen or world width | Polyline (OBJ `l`) or thin tube (mesh formats) |
| 7 | `TUBE` (v2) | Line with radius r | Capsule / capped cylinder | Tube |
| 8 | `DOT` | (.5,.5,.5) | Small sphere, configurable radius | Point (OBJ `p`, PLY vertex) or icosphere |
| 9 | `GRID` | The 12 cube edges | 12 thin cylinders, or a wire material on a box | 12 tubes or line segments |
| 10 | `MESH` | Quad sweep prev→current | Per-instance triangles in a BLAS (8 verts / 12 tris) | The same 12 triangles, with interpolated colours |
| 11 | `TRIANGLE` | p1, p2, p3 in `triangles` | BLAS triangle | 1 triangle |

Per-kind constants (unit vertices, index buffers, LOD tables) live in **one module**,
`structura.core.geometry.unit_shapes`. The viewport, the CPU/GPU BLAS builder and the exporters all import
them (DRY).

### 2.3 Aux tables

| Table | Columns |
|-------|---------|
| `MeshSweepTable` | `prev_xform f4 (M,3,4)`, `prev_rgba f4 (M,4)` |
| `TriangleTable` | `p f4 (T,3,3)` (object space) |
| `TemplateCallTable` | `template_id u2`, `emit_index u4` (position in the emission sequence) |
| `ParamTable` | `param f4 (N_p, 4)` for parameterised kinds (`cone[r]`, `torus[r]`, `tube[r]`) |

## 3. Materials

`MaterialLibrary` resolves every instance's `material` id to a `Material`:

```python
@dataclass(frozen=True)
class Material:
    name: str
    model: MaterialModel = MaterialModel.PRINCIPLED      # PRINCIPLED | CONSTANT | WIREFRAME | AO | DEBUG_*
    base: ColorSource = ColorSource.STATE                # STATE (instance rgba) or a fixed colour
    base_color: RGB = (0.8, 0.8, 0.8)
    metallic: float = 0.0
    roughness: float = 0.5
    specular: float = 0.5              # dielectric F0 scale (0.5 → 4%)
    ior: float = 1.5
    transmission: float = 0.0
    transmission_roughness: float = 0.0
    emission: RGB = (0, 0, 0)
    emission_strength: float = 0.0
    opacity: OpacitySource = OpacitySource.STATE         # instance alpha or fixed
    coat: float = 0.0
    coat_roughness: float = 0.03
    anisotropy: float = 0.0            # brushed metals (Sunflow ward / anisotropic ward)
    anisotropy_rotation: float = 0.0
    attenuation_color: RGB = (1, 1, 1) # Beer–Lambert inside transmissive materials (Sunflow glass absorption)
    attenuation_distance: float = math.inf
    thin_walled: bool = False
    # Legacy (Structure Synth internal raytracer), used by the `classic` integrator and migration:
    legacy_ambient: float = 0.6
    legacy_diffuse: float = 0.6
    legacy_specular: float = 0.6
    legacy_reflection: float = 0.0
```

**Resolution order** for each instance:

1. The v2 `material` declaration matching the tag (or the `mat` state).
2. A built-in preset with the same name as the tag (v2).
3. The default material.

Legacy `set raytracer::[TAG::]reflection|phong` values are applied to the `legacy_*` fields and mapped
onto the principled parameters by the migration rule in [10](10-renderer-shading.md) §6.2.

The principled parameter set is deliberately close to **UsdPreviewSurface**, **glTF PBR (metal-rough +
KHR_materials_transmission/ior/emissive_strength/clearcoat)** and **Blender Principled BSDF**. Export is then
a renaming, not an approximation ([15](15-export.md) §4).

## 4. Lights & environment

```python
class LightKind(Enum): POINT; SPHERE; SPOT; SUN; RECT; MESH   # MESH = emissive material geometry (implicit)
@dataclass(frozen=True)
class Light: name: str; kind: LightKind; position: Vec3; direction: Vec3; color: RGB
             intensity: float; radius: float; angle_deg: float; cone_deg: float; blend: float; size: Vec2
class EnvKind(Enum): COLOR; GRADIENT; SUNSKY; HDRI
@dataclass(frozen=True)
class Environment: kind: EnvKind; color: RGB; top: RGB; bottom: RGB; hdri_path: Path | None
                   rotation_deg: float; intensity: float; sun: str | None; turbidity: float; ground: RGB
                   visible_to_camera: bool = True
```

**Defaults when the script declares nothing:**

| Integrator | Default lighting |
|------------|------------------|
| `classic` | The legacy point light, derived from the camera exactly as 1.5 did |
| `ao` | White environment with AO, like `Sunflow-Colored.rendertemplate` |
| `path` | A "Studio" preset: gradient environment + soft sun at 45° elevation |

The background colour is visible to the camera unless an HDRI or sun-sky environment is chosen.

## 5. Camera

```python
class CameraKind(Enum): PERSPECTIVE; ORTHOGRAPHIC; SPHERICAL; FISHEYE
@dataclass(frozen=True)
class Camera:
    kind: CameraKind = CameraKind.PERSPECTIVE
    eye: Vec3; target: Vec3; up: Vec3
    fov_y_deg: float = 22.0              # legacy default
    ortho_height: float = 10.0
    aperture_radius: float = 0.0         # 0 = pinhole
    focus_distance: float | None = None  # None = distance(eye, target)
    blades: int = 0                      # 0 = circular bokeh
    blade_rotation_deg: float = 0.0
```

**Legacy conversion (exact).**

- Legacy view: `V = T(t)·S(s)·R·T(−p)`. A uniform world scale in front of a perspective camera is the same as
  moving the eye by 1/s. So:
  - `eye = p + Rᵀ·(−t/s)`;
  - `forward = Rᵀ·(0,0,−1)`;
  - `up = Rᵀ·(0,1,0)`;
  - `target = eye + forward·(|t_z|/s)`;
  - `fov_y = perspective-angle`.
- The reverse mapping ("copy camera to script", v1 syntax) writes `translation`, `rotation`, `pivot = target`
  and `scale`, choosing s = 1 and t = (0, 0, −|eye − target|).
- Round-trip is exact up to float error. Tests cover arbitrary legacy triples.

**Script camera vs interactive camera.** In 1.5, every build re-applied `set translation/rotation/...` and
snapped the view back. Structura applies the script camera:

- on the first build after opening a file;
- when the camera lines themselves change;
- when **View ▸ Camera ▸ Lock to script** is on.

Otherwise interactive navigation persists across rebuilds.

## 6. Render settings

`RenderSettings` is a frozen dataclass generated from the **ParamSpec** tables of the integrator, sampler,
film and output registries ([02](02-architecture.md) §6.2). So the UI, CLI flags, script `render {}` block,
legacy `set raytracer::*` keys and project serialisation all derive from one declaration.

Merge precedence, lowest to highest:

1. Registry defaults.
2. Legacy `set raytracer::*`.
3. v2 `render {}` block.
4. Project overrides (UI).
5. CLI flags.

## 7. Streaming chunks

During a build, the BuildService emits `SceneChunk(start, stop, instances_view)` objects that reference
rows `[start, stop)` of the growing arrays. They are copied into immutable arrays at slice boundaries.

- The viewport appends chunks to its GPU instance buffer.
- The final `SceneIR` is assembled once, at the end. The chunks' arrays are concatenated (there is no
  per-object Python work).

## 8. Project file (`.structura`)

UTF-8 JSON, designed to be diff-friendly. The script text is embedded, or linked when it lives in a separate
`.es` file.

```json
{
  "format": "structura-project",
  "format_version": 1,
  "app_version": "1.0.0",
  "script": { "mode": "embedded", "dialect": 1, "text": "set maxdepth 400\n..." },
  "seed": 42,
  "auto_increment_seed": false,
  "params": { "angle": 20.0, "iterations": 6 },
  "camera": { "kind": "perspective", "eye": [0, 0, 50], "target": [0, 0, 0], "up": [0, 1, 0], "fov_y_deg": 22 },
  "camera_lock_to_script": false,
  "render": { "integrator": "path", "samples": 512, "size": [1920, 1080], "view": "agx" },
  "materials": { "shiny": { "roughness": 0.1 } },
  "lights": [],
  "environment": { "kind": "sunsky", "turbidity": 3.0 },
  "timeline": { "fps": 30, "frames": 240, "tracks": [] },
  "export_presets": [],
  "thumbnail_png_b64": "iVBORw0KGgo..."
}
```

- The schema is versioned, and a migration function handles each version bump
  (`structura.core.scene.project_migrations`).
- **Autosave:** every 60 s, to the user cache dir. On start-up after a crash, recovery is offered.
- Saving as `.es` writes the script only. "Export camera/render settings as `set` lines" produces a
  self-contained v1-compatible file (the 1.5 "autosave EisenScript" feature).

## 9. Colour pipeline (one place)

```
authored sRGB (script / UI)  ──►  linear Rec.709 (packers)  ──►  render/viewport (linear)
        ──►  view transform (sRGB standard | AgX | ACES fitted | Filmic)  ──►  display / 8-bit output
```

- The packers (`render.compile.pack_colors`, `viewport.upload.pack_colors`) call one function:
  `core.color.srgb_to_linear`.
- View transforms are SKL functions shared by the viewport and the film ([11](11-compute-backends.md)).
- EXR output stays linear; PNG/JPEG output is view-transformed.
