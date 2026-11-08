# Exporting

**File ▸ Export As…** (Ctrl+E) opens a Save As dialog that lists every format; the chosen file type (or a typed
extension) decides the format. **Export ▸ <format>…** does the same for one format. The dialog starts in the
folder you last exported to (else next to the script, else *Documents/Structura*).

The **export sheet** that follows shows:

- **Save to:** the full path, with **Change…** to pick another;
- **Contents:** the objects by kind;
- **Preset:** saved option sets for this format — **Save Preset…** keeps the current options under a name
  (`structura export --preset NAME` uses the same presets);
- the format's **options** (the same options the command line takes with `--option KEY=VALUE`).

Exports run in the background; a toast says when the file is written, with **Show in Folder**.

**Render templates** (Structure Synth's `.rendertemplate` files) can name a program to run on the exported file
(Sunflow-Colored runs Sunflow through `%SUNFLOW%`). Structura shows the command, with any environment variable
that is not set, and runs it only if you agree (once per command and session). Its output goes to the Console.

## Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| Wavefront OBJ + MTL | `.obj` | Groups by colour, tag or material; vertex colours; streamed (any size). "obj-legacy" reproduces Structure Synth's layout |
| PLY | `.ply` | Binary, vertex colours |
| STL | `.stl` | 3D printing: millimetres, on the build plate, optional **watertight** union |
| 3MF | `.3mf` | Colour 3D printing; instanced components (one object for the slicer) |
| glTF / GLB | `.gltf` `.glb` | PBR materials, camera; optional `EXT_mesh_gpu_instancing` |
| USD | `.usda` `.usdc` `.usdz` | PointInstancers, UsdPreviewSurface materials, camera, lights; *flattened* mode; *matrix* shear policy |
| X3D / VRML97 | `.x3d` `.wrl` | Web and CAD viewers; DEF/USE prototypes with exact transforms |
| Blender script | `.py` + `.npz` | Run in Blender ≥ 4.2: meshes or Geometry Nodes instances, Principled materials, camera, world, Cycles |
| POV-Ray 3.8 | `.pov` | Native shapes with matrices, finishes from materials, radiosity |
| Sunflow | `.sc` | Instanced meshes, shaders, sun-sky — renders in the original Sunflow |
| Mitsuba 3 | `.xml` | Shape groups and instances, principled BSDFs, meshes as PLY files |
| Render templates | `.pov` `.sc` `.rib` `.xml` `.txt` | Structure Synth's `.rendertemplate` files, unchanged (format "template") |

## Shared options

- **lod:** detail of round shapes (low … ultra).
- **up:** Y-up (glTF, USD default) or Z-up (Blender, printing).
- **unit_scale:** world units to file units (STL and 3MF default to 10 mm per unit).

## 3D printing

- **STL watertight** merges every object into one closed solid (manifold3d), ready for slicing.
- **CSG markers:** Structure Synth's `template::union-begin … union-end` (and `difference`, `intersection`)
  group objects for boolean operations. With the **csg** option (STL, PLY, 3MF) they are evaluated, so the
  classic "CSG test" example prints without POV-Ray.
- Both STL and 3MF place the structure on the build plate (lowest point at z = 0).

## Sheared instances

Structure Synth's `matrix` and non-uniform scale followed by rotation give *sheared* instances, which
formats limited to translation/rotation/scale cannot hold. Structura bakes those into meshes (glTF, USD
default), or places them exactly where the format allows a full matrix (3MF, X3D, VRML, POV-Ray, Sunflow,
Mitsuba, USD with `shear=matrix`). The export summary says how many were baked.
