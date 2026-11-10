# KnotPlot — Detailed Feature Inventory

Research date: November 10, 2026  
Product: KnotPlot, by Robert G. Scharein / Hypnagogic Software  
Scope: Desktop application, bundled research and demonstration tools, documented interchange formats, and separately identified website/companion resources.

## 1. Scope, evidence, and completeness

This is a comprehensive inventory of publicly documented capabilities, not a claim to enumerate every internal command or every control in every build. It combines the current download page, the main product website, the September 5, 2019 PDF manual, the August 11, 2022 demo guide, specialist TopoICE manuals, and explicitly marked legacy HTML documentation. The application has not been installed or tested for this inventory.

The online HTML manual explicitly says it is out of date. Even the PDF manual describes only part of the program. Consequently, undocumented capabilities and changes in current builds may not appear here. A feature documented in an older source is not automatically confirmed to work unchanged in the current release. [web:7][web:15]

### Evidence labels

- **Current listing**: explicitly described by the current official website or download page.
- **PDF-documented**: described in the 2019 application manual.
- **Demo-documented**: described in the 2022 demo guide; a demonstration is not necessarily a general-purpose tool with a separately documented API.
- **Specialist-documented**: described in a TopoICE manual.
- **Legacy-documented**: described in the explicitly outdated HTML documentation; verify current syntax and availability.
- **External dependency**: requires or is described as cooperating with other software.
- **Companion resource**: related website or separate program, not counted as a built-in application capability.

Entries separate capabilities where useful, but overlap is intentional: creating a braid, warping a braid, and watching a braid demonstration represent different aspects of the same underlying machinery. No arbitrary total feature count is asserted.

## 2. Product and platform baseline

| Item | Documented detail | Qualification |
|---|---|---|
| Current marketed version | KnotPlot 1.022 | Current official download-page listing at the research date. |
| Windows | Windows 10/11 downloads; build 5144 | Both ordinary and non-administrator installers are listed. |
| macOS | Separate Apple-silicon and Intel downloads; build 5145 | Check the platform-specific installation notes and current requirements. |
| Linux | ARM64 and x86-64 executables; build 5093 | An alternate x86-64 executable is also offered. |
| Graphics foundation | OpenGL application | Platform availability does not imply identical behavior on every graphics device. |
| Distribution layout | Windows/macOS package application and supporting distribution together | Linux executable and supporting distribution are downloaded separately. |
| Evaluation edition | Free evaluation download | Many features are disabled; no exhaustive current entitlement matrix is supplied. |
| Full edition | Key unlocks the full version | The listed price is US $27.18; verify before purchase. |
| License-related benefits | Free upgrades and non-expiring software are advertised | These are product terms, not mathematical features. |
| Embedded scripting | Lua on macOS, Windows 10/11, and Linux | Current listing; the 2019 manual predates this addition. |

Source: current download page and main website. The platform builds are not synchronized, so do not assume identical newest functionality across operating systems. [web:8][web:11]

## 3. Mathematical objects and underlying representations

| Feature | What it enables | Evidence / caveat |
|---|---|---|
| Closed mathematical knots | Work with a closed single-component curve embedded in three-dimensional space. | PDF-documented. |
| Multi-component links | Work with several closed components together. | PDF-documented. |
| Open strings | Keep curves open instead of requiring closure. | PDF-documented. |
| Braids | Generate and manipulate braid-based constructions. | PDF- and demo-documented. |
| Knotted graphs | Model embedded graphs whose edges can be knotted or linked. | Implemented through bead identifications; not restricted to disjoint circles. |
| Polygonal knot representation | Represent curves through vertices called beads and connecting segments. | The underlying piecewise-linear object differs from its smoothed visual tube. |
| Smooth tube representation | Display interpolated tubular surfaces around the curve. | Display/surface geometry rather than a separate proof of topology. |
| Four-dimensional surfaces | Construct and visualize knotted and linked spheres in four dimensions. | Higher-dimensional geometry is projected for viewing. |
| Per-component attributes | Store component state and some appearance attributes in native files. | Legacy file-format documentation describes closure, color, and string width. |

Sources: PDF manual, demo guide, and file-format specification. [web:15][web:14][web:18]

## 4. Catalogues, discovery, and loading

| Feature | Detail | Access / qualification |
|---|---|---|
| Large included knot/link database | The main website advertises more than 3,000 knots and links. | Current listing; not a claim that every object has the same metadata. |
| Rolfsen catalogue coverage | The PDF manual describes the complete Appendix C catalogue, about 384 entries. | This is a named subset, not the current total database size. |
| Named catalogue loading | Load specific catalogue entries such as the trefoil with `load 3.1`. | PDF-documented. |
| Multi-component naming convention | Link filenames encode crossing number, component count, and table index. | See the PDF manual for exact naming conventions. |
| Special collection | Load unusual, named, composite, or nonstandard configurations. | `knot special`; named examples include granny and square knots. |
| Random selection | Choose a random knot or link from the catalogue. | `knot`. |
| Component-count selection | Randomly select entries with a specified number of components. | The manual documents one through four components for this selector. |
| Catalogue-index selection | Load by numerical position in a table. | The documented 1–384 range belongs to the older Rolfsen table mechanism. |
| Interactive knot zoo | Browse a grid of knot thumbnails and click an entry to load it. | `zoo start size`. |
| Configurable zoo size | Change how many entries appear in a zoo grid. | Size controls / command argument. |
| Random zoo | Display a randomly chosen set of catalogue entries. | `zoo` controls and random-zoo buttons. |
| Torus-knot zoos | Browse torus-knot collections, including randomized selections. | Main-panel controls described in the PDF manual. |
| External knot loading | Read saved knot/link coordinate files. | `load filename`. |
| Union/combine loading | Add a loaded object to the currently loaded object. | `load combine filename`. |
| Connected/direct sum loading | Build a composite knot from current and loaded knots. | `load sum filename`; manual expects proper knots and notes possible manual adjustments. |

Sources: current website, PDF manual, and introductory handout. [web:11][web:15][web:9]

## 5. Construction and procedural generation

| Feature | Detail | Commands / controls |
|---|---|---|
| Hand sketching in 3D | Place beads interactively and indicate over/under crossings through mouse input. | Sketch panel. |
| Torus knots | Construct parametrized torus knots. | `torus n m [beads]`. |
| Torus links | Non-coprime torus parameters produce a multi-component link. | Number of components is `gcd(n,m)`. |
| Random torus parameters | Omit torus parameters to allow randomly chosen values. | PDF-documented. |
| Torus geometric controls | Set major radius, minor radius, and bead count. | `R-torus`, `d-torus`, `N-torus`. |
| Linked chains | Generate chains with configurable component and bead counts. | `chain ncomp [nbeads]`; manual says component count should be even. |
| Chain scale controls | Adjust overall chain size and individual ring size. | `D-chain`, `d-chain`. |
| Lissajous knots | Construct curves from frequency and phase parameters. | `lissajous nx ny nz [phix phiy nbeads]`. |
| Two-mode Lissajous construction | Generate the additional documented Lissajous family. | `2lissajous`. |
| Unknot/circle constructor | Create a circular polygonal unknot with selected radius and bead count. | `unknot [B [R]]`. |
| Conway-notation construction | Translate Conway notation into a tangle-calculator construction. | `conway`; the 2019 PDF shows examples beyond the older HTML description. |
| Tangle calculator | Construct objects from a tangle command string or interactive calculator. | `tangle tangle-string`. |
| Rational tangles | Create rational tangles from fractions. | Demo guide examples: `tangle (3/2)` and `tangle (11/7)`. |
| Random tangles | Generate randomized tangle-based examples. | `random tangle`. |
| Tangle-holder constructions | Embed smaller tangles into holders/basic polyhedra to make complex knots and links. | Demo-documented. |
| Arbitrary braids | Generate braid configurations. | Construction panel and braid commands; exact grammar is not reproduced here. |
| User-defined constructors | Invoke distributed/custom constructor scripts with parameters. | `construct name ...`, using `KP-cons-name`. |
| Additive construction mode | Retain existing geometry when adding certain newly generated objects. | `new = false`; not every constructor is claimed to honor this parameter. |
| Twist-knot family exploration | Demonstrate how twist knots are constructed. | Demo-documented, not a separately verified general command. |
| Turk’s Head knot family | Create alternating constructions derived from torus knots. | THK demo. |

Sources: PDF manual and 2022 demo guide. For Conway notation, prefer the later PDF over the older HTML claim that only rational cases are supported. [web:15][web:14][web:17]

## 6. Celtic and decorative construction tools

| Feature | Detail | Qualification |
|---|---|---|
| Celtic Knot Construction Engine | Built-in machinery for Celtic-style constructions. | Called CKCE in the demo guide. |
| Interactive Celtic knotting entry point | Reach Celtic construction from the Sketch panel. | Guide says Sketch, then “Celtic knotting” near the bottom. |
| Plaits | Generate complex plait-like Celtic constructions. | `plaits` demo. |
| Spherical plaits | Generate plait constructions on a spherical layout. | `splaits` demo. |
| Star-like constructions | Generate Celtic-flavored star designs. | `star/box` demo. |
| Box-like constructions | Generate Celtic-flavored boxes. | Same demo family. |
| Celtic cages | Construct cages used to trap other knots. | `trapped` demo. |
| Weaving-machine visualization | Use a knot as a weaver; the documented demo chooses torus knots. | `weave` demo; not a claim of textile-production output. |
| Antoine’s Necklace stages | Visualize initial stages of the fractal-link construction. | Finite construction/demo, not an infinitely resolved fractal. |

Source: 2022 demo guide. [web:14]

## 7. Editing, component management, and transformations

| Feature | Detail | Commands / caveats |
|---|---|---|
| Direct 3D manipulation | Drag portions of a knot through space. | Interactive manipulation described by the PDF manual. |
| Local force manipulation | Apply forces selectively to local regions. | PDF-documented. |
| Vertex/edge editing | Add, delete, and move vertices and edges. | Edit panel summary in TopoICE-X manual. |
| Open a component | Convert closed components to open ones. | `open`, `open all`. |
| Close a component | Join a component’s endpoints to close it. | `close`, `close all`. |
| Cut at a bead | Open a closed component or split an open one. | `cut bead`; very small components may be removed automatically. |
| Join endpoints | Connect endpoints of open components. | `join a b`. |
| Delete component | Remove a chosen component, or all components. | `delete`, `delete all`. |
| Isolate component | Keep one component and remove the others. | `keep component`. |
| Swap components | Change component ordering. | `swap compa compb`. |
| Reverse bead order | Reverse the ordering/orientation of one or more components. | `revbeads [comp]`. |
| Shift bead numbering | Move the starting index around a component. | `shift distance [comp]`. |
| Change bead count | Set, increment, decrement, or multiply bead count. | `nbeads`, `nbeads mult`. |
| Segment subdivision | Split every segment, a selected segment, or segments exceeding a length threshold. | `split`, `split cylinder n`, `split value`. |
| Graph identification | Identify beads to create graph vertices/junctions. | `identify a b`. |
| Reset graph identifications | Remove bead-identification relationships. | `identify init`. |
| Cable construction | Transform a knot into a cabled construction. | `cable`. |
| Doubling | Produce doubled-knot constructions. | `double`. |
| Companion transformation | Apply the documented companion-knot transformation. | `companion`; manual restricts it to one component. |
| Satellite knots | Build satellite constructions through braid/warp machinery. | Demo guide describes `braid` and `warp`. |
| Braid warping | Warp a braid into another spatial configuration. | Demo-documented. |
| Anchors | Use anchors in dynamical manipulation. | Supported and drawable; demo guide calls its anchor example incomplete. |
| Undo control | Undo some operations. | Specialist manual says undo “often” works; universal history/redo is not established. |

Sources: PDF manual, demo guide, and TopoICE-X panel summary. Component numbering starts at zero in documented component-editing commands. [web:15][web:14][web:16]

## 8. Geometric transformations

These change the stored embedding, unlike view-only camera operations. Arbitrary modifications should not be assumed to preserve knot type. [web:15]

| Feature | Detail | Access |
|---|---|---|
| Spatial rotation | Rotate stored coordinates about a chosen axis, optionally for a component. | `about`. |
| Relative translation | Move geometry by an offset vector. | `translate`. |
| Absolute positioning | Position an initial bead at specified coordinates. | `translate to`. |
| Nonuniform scaling | Scale stored coordinates independently by axis. | `scale xs ys zs [comp]`. |
| Reflection | Reflect across selected coordinate directions; combined reflections allow inversion. | `reflect`. |
| Bounding-box centering | Center the object’s bounding region at the origin. | `centre`. |
| Center-of-mass centering | Center by the object’s center of mass. | `centre mass`. |
| Fit to radius | Scale to a desired overall radius. | `fitto`. |
| View-to-geometry rotation | Bake the current view rotation into the embedding. | `rotate fix`. |
| Jitter | Randomly displace beads. | `jitter distance`. |
| Mangling/crankshaft-like moves | Rotate a randomly selected arc about the line joining two beads. | `mangle`; do not presume collision-free behavior. |
| Swirl deformation | Apply an axis-based swirl, optionally choosing an axis randomly. | `swirl`. |
| Per-component targeting | Many geometric commands target one component or the last component. | Exact accepted arguments depend on the command. |

Source: PDF manual. [web:15]

## 9. Relaxation, dynamics, and experimental methods

| Feature | Detail | Qualification |
|---|---|---|
| Force-based relaxation | Smooth and simplify a conformation through simulated forces. | Not a guarantee of a global optimum or a topology proof. |
| Collision avoidance | Default damped model includes collision avoidance. | Helps prevent strands passing through one another under the documented model. |
| Collision-permitted dynamics | Allow crossings for experiments or different visual behavior. | May change knot type. |
| Damped dynamics | Dissipate motion toward a smoother configuration. | Main/Dyna panels. |
| Undamped dynamics | Retain motion in an alternative force model. | Manual’s B preset disables collision checking. |
| Dynamics presets | Switch quickly among documented force-law combinations. | Main-panel controls. |
| Force-law tuning | Change force settings during simulation. | Dyna panel and command interface. |
| Charge setting | Adjust a documented force-model charge value. | Legacy `charge`. |
| Spring constant | Adjust the Hooke-law setting. | Legacy `hooke`. |
| Force exponent | Change the dynamical-force exponent. | Legacy `power`. |
| Time increment | Adjust simulation time step. | Legacy `timeincr`; numerical stability is not guaranteed. |
| Continuous relaxation | Run until explicitly stopped. | `go`, stopped with `go 0` in the PDF manual. |
| Fixed iteration count | Run a selected number of relaxation steps. | `go niter`. |
| Atomic iteration execution | Run iterations atomically. | `ago niter` in PDF manual. |
| Background relaxation | Continue rotating or changing display settings while relaxing. | PDF-documented. |
| Velocity reset | Zero bead velocities. | Main-panel zero button; relevant to undamped motion. |
| Dynamics reset | Restore the default force model and sliders. | Init control. |
| Adaptive simplification | Remove excess string in loose regions and add detail in tight ones. | Split/delete demo; the guide explicitly notes a difficult exception. |
| Gravity force | Explore gravitational dynamics. | Gravity demo with several sub-demos. |
| Free dragging | Pull an open string interactively in three dimensions. | Free Drag demo. |
| Ring packing | Pack rings or other objects with adjustable size and thickness. | Demo-documented. |
| Random-knot algorithms | Explore hedgehog and crankshaft algorithms. | Demo-documented; no uniform-sampling guarantee is stated. |
| Minimal-stick experiments | Script searches for low-stick conformations. | PDF describes experimental searches, not universal exact minimization. |
| Random-knot experiments | Use commands/scripts to generate and explore random configurations. | PDF-documented. |
| Regional tangle relaxation | Relax inside a sphere, outside it, or the entire object. | TopoICE-Dynamics. |
| Display-step tuning | Redraw after a configurable number of dynamical steps. | TopoICE-Dynamics `dstep` control. |

Sources: PDF manual, legacy command reference, demo guide, and TopoICE-X manual. [web:15][web:17][web:14][web:16]

## 10. Topology and geometric measurements

| Feature | What is computed or explored | Dependency / limitation |
|---|---|---|
| Gauss code | Diagram-based encoding of a knot or link. | `gauss`; PDF-documented. |
| Dowker / DT code | Dowker encoding of the current knot diagram. | `dowker`; PDF manual documents single-component use. |
| Interactive code exploration | Examine DT and Gauss encodings interactively. | Codes demo, with additional on-screen help. |
| Alexander polynomial | Polynomial knot invariant. | Manual describes integration requiring Mathematica; single-component use. Do not assume a self-contained current calculator. |
| HOMFLY polynomial | Polynomial invariant through cooperation with other software. | Manual explicitly describes polynomial calculations as external-software integration. |
| Writhe | Geometric/diagram-related quantity listed among computable properties. | Listed in PDF overview; no universal current command syntax asserted here. |
| Average crossing number | Compute/explore ACN. | PDF feature overview; guide supplies static and dynamic visualization demos. |
| Thickness | Compute a knot-thickness quantity. | Listed in PDF overview; distinguish from visual tube radius. |
| Simon minimum-distance energy | Evaluate the documented knot/link energy. | `energy`. |
| Object information | Report bead count, component count, and spatial extents. | `information`. |
| Coordinates | Print or export bead coordinates. | `coords`, legacy reference. |
| Physical/topological computation panel | Access computations through the Comp panel. | Panel summary in TopoICE-X documentation. |

Sources: PDF manual, demo guide, legacy commands, and specialist panel summary. Matching polynomial values alone should not be interpreted here as a built-in general proof that two arbitrary knots are identical. The documentation does not establish a universal knot classifier. [web:15][web:14][web:17][web:16]

## 11. Four-dimensional construction and visualization

The application’s four-dimensional functionality includes surfaces such as knotted 2-spheres. This differs from simply displaying a three-dimensional curve from another angle. [web:15]

| Feature | Detail | Evidence |
|---|---|---|
| Knotted/linked spheres in 4D | Interactively construct higher-dimensional surfaces. | PDF overview. |
| Spun-knot construction | Spin a knot about a selected plane to create a knotted sphere. | Legacy `spin`; basic spun-trefoil demo. |
| Spin-plane placement | Define a spin plane using bead locations and an angle. | Legacy `splane`. |
| Spin-plane display | Show or hide the construction plane. | Legacy special/control-panel options. |
| 4D rotations | Rotate in selected coordinate planes of four-space. | Legacy `4dplane` and spin controls. |
| Orthographic 4D projection | Project higher-dimensional geometry orthographically into 3D. | Legacy `4dto3d ortho`. |
| Perspective 4D projection | Use a four-dimensional viewpoint/eye-distance parameter. | Legacy `4dto3d persp`, `4deye`. |
| Hopf projection option | Use the documented Hopf mapping for projection. | Legacy `4dto3d hopf`; not identical to every Hopf-fibration demo. |
| Partial spun-surface display | Enable selected latitude ranges of a spun surface. | Legacy `spactivate`. |
| Spinning animation | Animate a knot spun in four dimensions. | Legacy `smovie`; spun-trefoil demo. |
| Spun-surface model export | Export NURBS or polygonal representations. | Legacy `spdxf`, `spface`, `spsdl`; verify current exporters. |
| Dedicated 4D panel | Interactive controls for higher-dimensional functionality. | PDF and specialist panel descriptions. |

Sources: PDF overview, legacy command reference, and basic demo documentation. Legacy command details are not independently confirmed in the latest build. [web:15][web:17][web:21]

## 12. Viewing, rendering, and appearance

| Feature | Detail | Qualification |
|---|---|---|
| Virtual-trackball rotation | Rotate the view with mouse dragging. | View-only operation. |
| View scaling | Enlarge or shrink the displayed scene. | Distinct from scaling stored coordinates. |
| Scene translation | Pan the displayed scene. | Main-panel summary describes middle-mouse translation. |
| Restore viewing transform | Return to the default orientation/transform. | `untran` control; `rotate unit` resets rotation. |
| Orthographic camera | Set orthographic viewing bounds. | `ortho`. |
| Non-proportional view scaling | Distort the view along separate axes. | `nonprop`; not the same as stored geometry scaling. |
| Smooth tubes | Interpolated tube display. | `mode s`. |
| Beads and cylinders | Display the underlying polygonal representation. | `mode b`, `mode c`, and combinations. |
| Force vectors | Display dynamical-force directions. | `mode f`. |
| Anchor visualization | Draw anchor markers. | `mode a`. |
| Graph-junction visualization | Draw bead-identification clusters. | `mode C`. |
| Combined drawing modes | Combine compatible modes, e.g. beads, cylinders, and forces. | `mode cfb` example. |
| Flat shading | Use a flat-shaded appearance. | `draw flat`. |
| Spectrum style | Apply spectrum-type drawing. | `draw spectrum`. |
| Broken surfaces | Offset/disjoin surface elements for special effects. | `draw broken`, `broff`. |
| Broken spectrum combination | Combine broken and spectrum effects. | `draw sbroken`. |
| Material colors | Set colors through RGB or HSV controls. | `matrgb`, `mathsv`; numeric conventions differ between old sources, so check current help. |
| Component hue sequencing | Choose initial hue and hue increment across components. | `hstart`, `hincr`. |
| Automatic component colors | Set component hue increments automatically on loading/construction. | `auto-colour`. |
| Saturation and brightness | Adjust smooth-tube color saturation and value. | `saturation`, `value`. |
| Background color | Change view background color. | `background`. |
| Tube radius | Adjust display/export tube thickness. | `cyl-rad`; not a topological invariant. |
| Circumferential tessellation | Control sides around a tube. | `nsegments`. |
| Along-curve interpolation | Control interpolation between beads. | `ncurve`. |
| Fast/high-quality presets | Trade visual detail for rendering speed. | `cheapo`, `luxo`. |
| Twist/closure seam correction | Reduce the displayed tube’s deficit-angle seam. | `twfix`. |
| Grid configuration | Set rectangular/polar-like grid mode, spacing, and size. | `grmode`, `grsize`, `grspace`, `grSpace`. |
| Axes and bead labels | Show orientation aids and vertex indices. | Legacy `special axes`, `special labels`. |
| Utility sphere/backdrop | Show auxiliary scene objects. | Legacy special-display options. |
| Z-buffer control | Enable or disable depth buffering. | `zbuffer`. |
| Blending control | Change low-level blend factors. | `blendfunction`; hardware-dependent behavior is documented. |
| Transparency experiments | Alpha/pseudo-transparent effects. | Legacy documentation warns transparency is not generally correct without draw ordering. |
| Framebuffer persistence | Leave traces or paint effects by controlling buffer clearing. | `clrfun`. |
| Single/double buffering | Choose visible drawing or off-screen-buffered rendering. | Legacy `sbuffer`, `dbuffer`. |
| Display refresh control | Force a redraw or suspend normal drawing. | `display`, `Drawing`. |
| Legacy NURBS preview | Draw an explicit NURBS surface preview. | `dnurbs`; old documentation calls it slow/not recommended. |
| Legacy graphical-object acceleration | Cache/render an object through an older display mechanism. | `makeobj`, `mode o`; do not assume modern GPU acceleration claims. |

Sources: PDF manual, legacy command reference, and specialist main-panel summary. [web:15][web:17][web:16]

## 13. Images, vector graphics, and publication output

| Feature | Detail | Qualification |
|---|---|---|
| View-window image capture | Save the displayed view as an image. | `imgout`; current listing says several picture formats without enumerating all. |
| Encapsulated PostScript export | Produce high-quality lightweight vector figures. | `psout`; explicitly advertised for LaTeX/Illustrator workflows. |
| Multiple PostScript styles | Change figure style through `psmode`. | PDF examples show multiple modes. |
| Bounding-box choices | Use full-page, tight, or square bounding boxes. | `psoption bbox`. |
| Output-extension settings | Configure the PostScript filename extension. | `psoption extension`. |
| PostScript font selection | Change output font settings. | `psoption font`. |
| PostScript textures | Configure a texture file for supported PostScript modes. | `psoption texture`; mode-dependent. |
| Page-size options | Select page size for vector output. | Official Merge3 example uses `psop pagesize a4`. |
| Headless figure generation | Run a script in non-graphics mode to produce an EPS file. | Official Merge3 example. |
| Control-panel PostScript | Export a representation of the current control panel. | Legacy `panel psout`. |
| ASCII-art rendering | Generate a text-mode picture. | `ascii`; useful in non-graphics sessions. |
| PPM raster output | Save Portable Pixmap image data. | Legacy `ppmout`; supports reduction factor. |
| SGI RGB output | Save a Silicon Graphics RGB image. | Legacy `rgbout`. |
| Imager RLE output | Save an Imager run-length-encoded image. | Legacy `rleout`. |
| External EPS-to-PDF workflow | Convert exported EPS to PDF using Ghostscript. | Separate conversion step in the official example, not proof of universal native PDF export. |

Sources: current download page, PDF manual, legacy command reference, and official publication example. Do not infer PNG, JPEG, SVG, or native PDF availability merely from “several picture formats.” [web:8][web:15][web:17][web:4]

## 14. Surface-model export and interchange

| Format / feature | What is documented | Status / limitation |
|---|---|---|
| Wavefront OBJ | Polygonal model output through `objout`. | Current format listing and PDF manual. |
| DXF NURBS | Surface description through `dxf`. | Current DXF listing; detailed command in PDF. |
| DXF polygonal faces | Polygon export with optional broken-surface behavior. | `pfdxf`. |
| POV-Ray output | Output for external ray tracing. | Current official download-page listing; exact current command not established here. |
| Alias SDL NURBS | Surface representation with patch/shader names. | `sdl`; legacy renderer ecosystem. |
| Alias SDL polygonal output | Polygonal face/model descriptions. | `psdl`. |
| Basic Polygon Format | Export geometry for conversion/filtering pipelines. | `rawout`, BPF. |
| Dragon surface output | NURBS format for David Forsey’s Dragon. | Legacy `dragon`. |
| Optik patch output | Bezier-patch output. | Legacy `optik`. |
| Optik polygon output | Polygonal output. | Legacy `poptik`. |
| METAFONT export | Generate knot-related METAFONT programs. | PDF describes it as under development/test functionality. |
| External application workflows | Manual names Blender, Unity 3D, Maya, AutoCAD, and METAFONT. | Treat as interchange workflows, not verified native live plug-ins. |
| Export-detail controls | Tube radius and tessellation influence exported surfaces. | Distinct from just changing camera scale. |
| Higher-dimensional surface export | Export spun-surface representations through documented 4D exporters. | Legacy details in Section 11. |

The 2019 manual says its described surface-export commands expect smooth-tube mode and work on one component at a time; separate components can be exported using save/load/keep. This is a documented historical restriction, not a tested statement about every exporter in the newest release. Neither STL output nor fabrication-ready/watertight meshes are established by these sources. [web:8][web:15][web:17]

## 15. Native files and data exchange

| Feature | Detail | Qualification |
|---|---|---|
| Native knot save/load | Save and reopen mathematical curve data. | `save`, `load`; separate from saving a picture. |
| ASCII coordinate exchange | Read and write simple coordinate data. | PDF save options and legacy `coords`. |
| Save-format override | Choose a format for one save without changing the default. | `save filename [format]`. |
| Compact coordinate encodings | Documented choices include float, short, and char-style saves. | PDF names `LOCF`, `LOCS`, `LOCC` aliases. |
| Double-coordinate field | Native specification documents 8-byte double coordinates. | File-format field support, not an asserted modern menu option. |
| Multiple components per file | Store component boundaries and associated coordinate fields. | Native format specification. |
| Closure flags | Record whether a component is open or closed. | Specification describes default/attribute behavior. |
| Object naming | Store an optional object name. | Native field. |
| Graph gluing data | Store identifications for knotted graphs. | Native field. |
| Arbitrary metadata | Store name/value metadata. | Native field. |
| Component color and width | Store RGB color and string/cylinder width attributes. | Native field. |
| Date field | Store creation or other date information. | Native field. |
| Tangle-holder descriptions | Record tangle-holder construction information. | Native field. |
| Embedded command field | Native format can contain a KnotPlot command. | Legacy specification labels this expert functionality. |
| File-inspection example utility | `kpfsnoop.cpp` is described for examining native files. | Distribution/support utility, not a graphical feature. |
| File-writing example | `unknot.cpp` demonstrates writing a link file. | Support-code example. |

The old format page says KnotPlot uses “at least 22” input/output formats, but does not list all of them. That is a legacy lower-bound statement across input and output, not a verified current count of 22 export formats. [web:15][web:18][web:17]

## 16. Scripting, automation, and extensibility

| Feature | Detail | Qualification |
|---|---|---|
| Embedded Lua | Script within KnotPlot using Lua. | Current listing on Windows/macOS/Linux; no invented API catalogue. |
| Native command language | Enter commands interactively or execute command scripts. | Many functions are command-only. |
| Script-file execution | Execute a file with `<filename` or `read filename`. | Both documented; exact contexts can differ. |
| Non-graphics batch mode | Run without graphics for automation/research workflows. | `knotplot -nog`. |
| Optional control panel | Start without the control panel. | `-nopanel`. |
| Debug startup | Request debugging information. | `-debug`. |
| Numeric parameter assignment | Set parameters through `parameter = value`. | Real, integer, and Boolean settings documented. |
| Randomized arguments | Use documented random-value syntax for numeric parameters/arguments. | Uniform real/integer ranges and signed variants. |
| Random-seed control | Set the generator seed. | `seed value`; useful for repeatable setups within a given implementation. |
| Parameter inspection | List settings or settings matching a name prefix. | `parameters`, `parameters name`. |
| Path inspection | Inspect configured read/write paths. | `path`. |
| Timed pauses | Delay execution during scripted sequences. | `pause`. |
| Function-key bindings | Bind actions to function keys. | `function`; legacy references also describe shifted variants. |
| Parameter animation | Sweep a parameter over steps using linear/log progression. | Legacy `animate`. |
| Constructor extension mechanism | Dispatch named constructor scripts with arguments. | `construct`, `KP-cons-name`. |
| Shell integration | Invoke a host-shell command. | Documented on UNIX-like systems; prefix differs between older HTML and PDF, so verify installed help. |
| Version/environment inspection | Inspect version and distribution/resource directories. | `version`. |
| Execution statistics | Report execution information. | Legacy `statistics`. |
| Custom demo panels | Customize demo definitions through distribution/path files. | Legacy basic-demo documentation. |

Sources: current download page, PDF manual, legacy commands, and basic-demo documentation. This is not evidence of a public Python SDK, REST API, plugin marketplace, or supported remote service. [web:8][web:15][web:17][web:21]

## 17. TopoICE: DNA topology and tangle-equation tools

TopoICE is bundled with KnotPlot. The current download page names TopoICE-X and TopoICE-R and describes them as implementations of Isabel Darcy’s tangle-equation algorithms. These tools model topological aspects of DNA transformations; they are not atomistic molecular-dynamics packages. [web:8][web:16][web:22]

### 17.1 TopoICE-X: crossing changes and pathways

| Feature | Detail | Scope / limitation |
|---|---|---|
| Rational-knot input | Choose knots visually or enter rational fractions. | Zoo and numerical rollers/direct entry. |
| Dual diagram styles | Switch between catalogue-style images and rational-tangle notation. | `cat` / `rat` display modes. |
| One-crossing neighborhood | Find rational knots reachable from a given rational knot through one crossing change. | Manual specifies outputs through 13 crossings. |
| Pairwise crossing-change analysis | Determine whether a given pair can be related by one crossing change. | Within the tool’s rational-knot framework. |
| Distinct conversion displays | Show topologically different ways to make the change. | Solution navigation through up/down controls. |
| Neighbor navigation | Move through candidate target knots. | Next/previous controls. |
| Shortest-path search | Find all shortest paths within the documented rational-knot search graph. | Rational intermediate knots have fewer than 14 crossings. |
| Paths toward the unknot | Search shortest pathways to the unknot within that graph. | Not a general exact unknotting-number solver. |
| Path graph interaction | Click an edge to inspect its crossing change. | Specialist-documented. |
| Reverse pathway | Reverse a displayed path. | Specialist-documented. |
| Random knot-pair exploration | Generate example paths between randomly selected pairs. | Specialist-documented. |
| Recent pathway recall | Retain the last six requested pathways for convenient access. | Specialist manual’s UI behavior. |
| Diagram transfer to dynamics | Send a selected solution diagram to regional relaxation controls. | Green Get buttons. |

Important limitation: a shorter path might exist if non-rational knots were allowed as intermediates. “Shortest” is therefore conditional on the documented search space, not a global statement over all knots. [web:16]

### 17.2 TopoICE-R: recombination and tangle replacements

| Feature | Detail | Scope / limitation |
|---|---|---|
| Recombination modeling | Model topology changes for proteins binding two DNA segments. | Topological model of recombinase-like action. |
| Substrate/product input | Select initial and final rational knot configurations. | Visual zoo or fraction entry. |
| Initial bound-tangle input | Specify the initial DNA shape bound by the protein complex. | Visual or numerical input. |
| Tangle-equation solving | Solve the documented pair of numerator-closure equations for a replacement tangle and outside configuration. | See equations below. |
| Solution-family exploration | Browse parameterized families rather than only one diagram. | Manual examples use i, k, or h controls depending on family. |
| Family switching | Move among solution families. | Up/down controls. |
| Replacement filtering | Restrict the replacement fraction `f2/g2`. | Filter control. |
| Relaxation transfer | Send solution diagrams to TopoICE-Dynamics. | Get controls. |
| Infeasibility messages | Report when a specified conversion cannot occur under the chosen move. | Within the implemented assumptions. |

The documented equation system is:

```text
N(U + f1/g1) = N(A/B)
N(U + f2/g2) = N(Z/V)
```

Here `N` denotes numerator closure, `N(A/B)` and `N(Z/V)` are the supplied rational knots, and `U` is assumed ambient-isotopic to a sum of rational tangles. The manual says TopoICE-R does not find every solution when `|f1*g2 - f2*g1| = 1`; some solution presentations may repeat. Its completeness statements are conditional, not universal. [web:22]

### 17.3 TopoICE-Dynamics

- Relax the tangle inside a specified sphere.
- Relax the configuration outside the sphere.
- Relax the entire configuration.
- Adjust the sphere radius, including disabling automatic radius selection.
- Tune how often simulation steps trigger a redraw.

These operations help turn diagrammatic solutions into more spatially interpretable configurations; a visual relaxation alone does not prove a biological mechanism. [web:16]

## 18. Educational, exploratory, and exhibition features

### 18.1 Mathematical demonstrations

| Demonstration | What it illustrates |
|---|---|
| Guess knot | Compare a trefoil and a complicated unknot; explore why appearance alone is unreliable. |
| (Un)knot? | Another example centered on recognizing whether a curve is knotted. |
| Perko pair | Animate two different-looking presentations into the same conformation. |
| Brunnian links | Remove components and explore the link’s Brunnian property. |
| Random braid | Explore braid diagrams and their relationship to knot construction. |
| Reidemeister moves | Visualize the three fundamental diagram moves. |
| Chirality | Compare knots and mirror images, including an achiral example. |
| Twist and torus knots | Explore recognizable infinite knot families. |
| Satellite knots | Show satellite construction through braid/warp methods. |
| Rational tangles | Visualize rational-tangle construction. |
| ACN | Static/dynamic explanations of average crossing number. |
| Codes | Interactively compute and explore DT/Gauss encodings. |
| Blackboard framing | Demonstrate blackboard framing; guide says it does not always work. |
| Möbius inversion | Show inversion through a sphere; this is not simply a Möbius-strip generator. |
| Magnetic-field visualization | Display field lines around a knot treated as a current-carrying wire. |
| Current-direction reversal | In selected magnetic demos, reverse a component’s current and inspect field changes. |
| Knotted graphs | Explore graph-based extensions of ordinary knot theory. |
| Hopf fibration | Visualize Hopf-fibration structures with randomized seeds. |

### 18.2 Construction and dynamics demonstrations

- Split/delete adaptive simplification.
- Adjustable force-law exploration.
- Free Drag in three dimensions.
- Knot-driven weaving.
- Ring packing.
- Hedgehog and crankshaft random-knot algorithms.
- Chain and random-chain generation.
- Cable and braid-warp construction animations.
- Rotating knots and their planar shadows.
- Gravity, including falling/tossing effects.
- Lorenz-attractor paths; explicitly described as unfinished.
- Turk’s Head knot construction.
- Celtic plaits, spherical plaits, stars, and boxes.
- Antoine’s Necklace construction stages.
- Trapped-knot cages.
- General relaxation examples; guide notes some may become unstable.
- Object tossing through a loop, with a follow-camera option.
- Anchor demonstrations; described as incomplete.

### 18.3 Full-screen continuous exhibitions

The guide lists eight never-ending exhibitions that run full-screen until interrupted:

1. Knots!
2. Fly thru
3. Frenetic
4. Poly dance
5. Paint 1
6. Paint 2
7. Aum Fly
8. Glue graphs

Most demos include some randomness, so rerunning them may produce different results. The guide warns that Paint exhibitions can flicker or work incorrectly on some graphics hardware. DemoA and DemoB are the primary entry points; some demos provide additional on-screen question-mark help. [web:14]

## 19. User interface and learning support

| Feature | Detail | Qualification |
|---|---|---|
| Three-window working layout | Main view, control panel, and command window. | Windows can be repositioned and resized. |
| Command interaction | Access advanced functions through text commands. | Some capabilities are command-only. |
| Panel interaction | Use buttons, sliders, tabs, and rollers. | Some operations are panel-only. |
| Context menus | Right-click control panel/command area for menus. | macOS guidance says to use KnotPlot’s menus rather than ordinary application menus. |
| Main panel | Loading, display, and core dynamics controls. | PDF-documented. |
| Display panel | Adjust view/display settings. | Specialist panel summary. |
| Dyna panel | Tune force laws and dynamical behavior. | Specialist panel summary. |
| Sketch panel | Interactive curve drawing and access to Celtic knotting. | Specialist summary and demo guide. |
| Edit panel | Vertex/edge editing. | Specialist panel summary. |
| Export panel | Figures and surface-model output. | Specialist panel summary. |
| Comp panel | Geometric/physical/topological calculations. | Specialist panel summary. |
| Surf panel | Color/surface-related controls. | Specialist panel summary. |
| Cons panel | Parametric construction including torus, Lissajous, chains, and braids. | Specialist panel summary. |
| Cat panel | Catalogue selection. | Specialist panel summary. |
| 4D panel | Higher-dimensional controls. | PDF/specialist summary. |
| TopoICE panels | X, R, and associated dynamics. | Specialist manuals. |
| DemoA / DemoB | Built-in demonstrations. | Current download page and demo guide. |
| Context-sensitive panel help | Help button provides information specific to the active tab. | Current listing. |
| Introductory handout | Quick orientation to loading, viewing, sketching, and relaxation. | Official linked PDF. |
| Five small tutorials | Additional tutorial exercises are linked from the download page. | `ex1.pdf` through `ex5.pdf`; not separately audited in this inventory. |
| Publication-output examples | Official scripts and examples explain EPS/PDF production workflows. | External documentation, not an extra installed feature. |
| Reset control | Return many settings and current state to their initial configuration. | PDF says reset affects far more than the view. |

Sources: current download page, PDF manual, specialist panel summary, and demo guide. The 2019 PDF warns that quitting does not prompt about unsaved changes; verify this behavior in the installed build rather than relying on an automatic save safeguard. [web:8][web:15][web:16][web:14]

## 20. Related resources that are not automatically desktop features

### Official website and browser viewer

The official website includes image galleries, ray-traced examples, PostScript/PDF examples, stick-number data, and browser-based knot viewers. Some site galleries advertise interactive 3D viewing with a VR option. These website capabilities should not be conflated with native desktop VR support. [web:11]

### Separate knot-identification pipeline

The Knotting Tools page distributes tools described for a HOMFLY-PT-based identification workflow:

```text
knot coordinates
  -> coords2egc
  -> extended Gauss code
  -> optional xinger simplification
  -> jhomfly
  -> HOMFLY-PT polynomial
  -> jidknot / related lookup scripts
```

The page describes `xinger` simplification using Reidemeister I and II moves. This is a companion command-line pipeline, not sufficient evidence that the complete pipeline is a built-in current KnotPlot feature. It also does not establish that a polynomial lookup uniquely classifies every possible knot. [web:20]

## 21. Practical workflows enabled by the documented feature set

These are synthesized workflows, not additional separately verified product features.

### A. Explore an existing knot

1. Load an entry by name or through a zoo.
2. Rotate/pan/scale the view.
3. Compare smooth-tube and beads-and-cylinders rendering.
4. Inspect bead/component counts or diagram codes.
5. Save the curve data separately from any rendered image.

Basis: catalogue, view, display, information, and save/load capabilities. [web:15]

### B. Build and simplify a new construction

1. Sketch a curve or use a torus/Lissajous/tangle constructor.
2. Inspect crossings and component structure.
3. Enable a collision-avoiding relaxation model when preserving topology is intended.
4. Run relaxation, making local edits or adjustments where necessary.
5. Save the resulting mathematical coordinates.

Basis: construction and relaxation documentation. No claim is made that relaxation always finds a canonical form or a globally minimal configuration. [web:15][web:14]

### C. Make a publication figure

1. Load or construct the desired object.
2. Set its orientation and output style.
3. Tune tube thickness, interpolation, and tessellation for the target representation.
4. Apply seam correction where needed.
5. Export EPS; optionally convert EPS to PDF externally.

Basis: PDF/manual output controls and official Merge3 script example. [web:15][web:4]

### D. Transfer a knot to a 3D tool

1. Distinguish camera orientation from stored-coordinate transformations.
2. Choose a documented mesh/surface format such as OBJ or DXF.
3. Use smooth-tube mode where required by the exporter.
4. Account for documented legacy single-component restrictions.
5. Inspect the imported model in the target tool rather than assuming manufacturing suitability.

Basis: geometry and surface-export documentation. [web:15][web:8]

### E. Investigate DNA-topology transformations

1. Choose TopoICE-X for crossing-change/pathway questions, or TopoICE-R for tangle replacements.
2. Supply rational-knot/tangle inputs using fractions or a zoo.
3. Enumerate the available solutions within the documented domain.
4. Inspect solution diagrams and, if useful, relax selected regions.
5. Report the solver’s restrictions together with any biological interpretation.

Basis: specialist manuals. [web:16][web:22]

## 22. Capability boundaries and items not established

The examined sources do not establish the following as supported current application features:

- A complete, up-to-date enumeration of every command and parameter.
- A current feature-by-feature evaluation-versus-paid entitlement table.
- A universal exact knot-recognition or equivalence-decision interface.
- Globally exact crossing-number, unknotting-number, stick-number, or energy minimization for arbitrary input.
- A guarantee that relaxation always preserves topology under every setting.
- A guarantee that all polynomial calculations are self-contained and dependency-free.
- Native desktop VR solely because the website has VR-enabled viewers.
- A public Python SDK, REST service, browser-hosted desktop replacement, or cloud collaboration system.
- Native SVG, STL, PNG, JPEG, or direct PDF export based only on the generic output claims reviewed here.
- Fabrication-ready meshes, watertightness checks, slicer integration, or knot-tying robot instructions.
- General atomistic DNA simulation or complete biochemical-mechanism inference.
- Universal undo/redo, autosave, or an unsaved-changes safety prompt in the newest build.

These are evidence gaps, not proof that a capability is impossible or absent. Consult installed help, release-specific documentation, or the developer before treating an unverified capability as a requirement.

## 23. Source map and documentation age

| Citation | Source | Role in this inventory |
|---|---|---|
| [web:11] | Official KnotPlot homepage | Current high-level purpose, more-than-3,000 database claim, galleries and website viewer distinctions. |
| [web:8] | Official download page, updated October 24, 2026 | Version/platform/build listings, Lua, licensing, formats, and bundled TopoICE. |
| [web:15] | KnotPlot PDF manual, September 5, 2019 | Main application feature descriptions, commands, parameters, limitations. |
| [web:14] | Rough Guide to the KnotPlot Demos, August 11, 2022 | Demonstration inventory, CKCE, exploration tools, and demo caveats. |
| [web:7] | Legacy HTML manual landing page | Explicit warning that HTML documentation is outdated. |
| [web:17] | Legacy HTML command reference, generated February 7, 1997 | Supplemental command and 4D details, marked legacy throughout. |
| [web:18] | Legacy native file-format documentation | Data model, fields, coordinate encodings, support utilities. |
| [web:16] | TopoICE-X manual | Rational crossing-change analysis, pathways, limits, panel overview. |
| [web:22] | TopoICE-R manual | Recombination modeling, equations, family navigation, completeness limits. |
| [web:21] | Basic Demos documentation | Custom demo definitions and spun-trefoil example. |
| [web:9] | Introductory handout | Quick-start interaction and named loading examples. |
| [web:4] | Official Merge3 PostScript example | Scripted headless EPS generation, page size, external PDF conversion. |
| [web:20] | Knotting Tools page | Separate coordinate/EGC/HOMFLY-PT identification pipeline. |

### Official source locations

- Homepage: <https://knotplot.com/>
- Download and documentation hub: <https://knotplot.com/download/>
- PDF manual: <https://knotplot.com/doc/KnotPlot-Manual.pdf>
- Demo guide: <https://knotplot.com/manual/guide/Rough%20Guide%20to%20the%20KnotPlot%20Demos.pdf>
- Legacy HTML manual: <https://knotplot.com/manual/>
- Legacy command reference: <https://knotplot.com/manual/commands.html>
- Native file-format notes: <https://knotplot.com/manual/FileFormats.html>
- TopoICE-X manual: <https://knotplot.com/download/TopoICE-Xmanual.pdf>
- TopoICE-R manual: <https://www.knotplot.com/download/TopoICE-Rmanual.pdf>
- Basic demos: <https://knotplot.com/manual/BasicDemos.html>
- Introductory handout: <https://knotplot.com/doc/handout.pdf>
- Merge3 output example: <https://knotplot.com/postscript/m/Merge3.html>
- Companion knotting tools: <https://knotplot.com/knottingtools/>

---

Prepared as an original feature-oriented synthesis, not a reproduction of the manuals. Source citations preserve the evidence trail; the source-location list keeps the Markdown useful outside this conversation.
