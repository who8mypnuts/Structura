# Cindermedusae — Detailed Features, Architecture, and Research Inventory

Research date: November 10, 2026  
Creator: Marcin Ignac / Variable  
Subject: The original C++/Cinder generative-creature artwork, its documented development and exhibition variants, its explanatory browser sketches, and separately identified related implementations.

## 1. Executive summary

Cindermedusae is a custom generative-art program that produces imaginary jellyfish-like sea creatures and renders them in a natural-history illustration style inspired by Ernst Haeckel. It combines procedural 3D geometry, parameterized morphology, animation, lighting-dependent hatching, noise-masked color layers, and high-resolution image composition. It was developed for the Written Images generative-book project rather than documented as a general-purpose commercial modeling package. [web:23][web:29][web:28]

Its central design is a system of interconnected, animatable parameters: a deformed spherical head provides attachment points for tentacles and hair; changing the parameters changes the creature. Parameter values can be randomized within visually useful ranges, and continuous parameters can be animated to move between creature forms. [web:23][web:29][web:37]

The most important distinction in this inventory is between four things:

1. The original native artwork and authoring application.
2. ProcessingJS/WebGL teaching examples explaining some of its algorithms.
3. Later demonstrated developments, including GPU animation and interactive exhibitions.
4. A separately indexed Unity port whose internal features could not be verified here.

They should not be treated as a single downloadable product with one verified feature list. [web:23][web:29][web:28][web:27]

## 2. Research scope and confidence labels

This inventory synthesizes several sources, not just the requested making-of article:

- The creator’s detailed making-of article.
- The creator’s original project page.
- Variable’s portfolio account, including later presentation contexts.
- The creator’s retrospective account of the parametric system.
- Independent contemporary coverage of Written Images.
- Search-index evidence for a Unity port and additional contemporary coverage.

No original executable was installed, no interactive sketch was executed, and no source repository was successfully inspected. Therefore, this document is a detailed public-documentation inventory, not a tested software acceptance report.

### Evidence labels used below

| Label | Meaning |
|---|---|
| Original | Explicitly described for the original artwork/program by its creator. |
| Tutorial | Demonstrated in an explanatory sketch; not automatically a production-application control. |
| Later demonstration | A later variant or presentation is explicitly documented, but release/build details are absent. |
| Interpretation | A technical explanation or workflow inferred from documented mechanisms, not an additional advertised feature. |
| Proposed | Mentioned as a future intention, not established as completed. |
| Unverified port | Another implementation is indexed, but its code and detailed functionality were not inspected. |
| Not established | The reviewed evidence does not verify the claimed capability. |

A larger feature count is not inherently more accurate. Related implementation details are separated where they answer different practical questions, but no artificial total count is claimed.

## 3. Identity, timeline, and versions

| Item | Finding | Qualification |
|---|---|---|
| Project name | Cindermedusae | Preserve this spelling when searching for code and documentation. |
| Author | Marcin Ignac | Variable credits concept and code to Marcin Ignac / Variable. |
| Earliest reviewed project-page date | July 15, 2010 | Page date, not a verified application release number. |
| Making-of article | December 25, 2010 | Detailed historical implementation account. |
| Book/project portfolio date | 2011 | Variable lists Written Images, Copenhagen, Denmark. |
| Interactive exhibition | Computational Aesthetics ’11, Vancouver | Confirms an interactive version existed, not its full control scheme. |
| Public-art display | October 2013, Toronto Metro stations, Drift:Synthesis | Confirms presentation of the artwork; not a software release. |
| Retrospective discussion | 2017 Eyeo talk, transcribed March 28, 2019 | Useful for the creator’s explanation of continuous parameterization. |
| Version numbering | No complete public version history established | Do not invent release numbers, platform builds, or update guarantees. |

Sources: creator’s project/article pages, Variable portfolio, and retrospective. Different dates describe inception, documentation, publication, and exhibition; they need not conflict. [web:29][web:23][web:28][web:37]

## 4. Core generative capabilities

| Capability | Detailed description | Evidence class |
|---|---|---|
| Procedural creature synthesis | Generate imaginary sea-creature forms from algorithms rather than assembling a fixed library of finished creatures. | Original. |
| Shared construction system | Different creatures share the same procedural morphogenesis despite differing in appearance and movement. | Original / portfolio description. |
| Deformed spherical base | Construct the main body/head from a sphere-derived form. | Original. |
| Hierarchical attachment | Generate connection points with the head, then use them to start appendages. | Original. |
| Tentacle generation | Build curved, tube-like appendages from procedural curves or polylines. | Original and tutorial explanation. |
| Hair generation | Generate hair from head connection points. | Original; the full hair algorithm is not separately documented. |
| Parameter-controlled morphology | Change form through a collection of variables rather than only direct mesh editing. | Original. |
| Randomized morphology | Randomize variables to create different creatures. | Original. |
| Animation of morphology | Animate parameters over time. | Original. |
| Species-like transitions | Smoothly vary the continuous parameter system to transform between fictive species. | Portfolio and retrospective. |
| Unique print instances | Generate distinct creatures for print compositions. | Original / portfolio; not a formal collision-free uniqueness guarantee. |
| Geometry independence from stock assets | Creator states that no predefined geometry is used. | Original. |
| Procedural visual treatment | Creator states that no predefined textures are used. | Original; does not mean texture coordinates or procedural noise are absent. |

Sources: original project description, making-of article, portfolio, and retrospective. “Infinite” variety is the project’s artistic description of its possibility space, not a measured count or a guarantee that finite-precision computation never repeats. [web:29][web:23][web:28][web:37]

## 5. Head and bell geometry

### 5.1 Parametric circular foundation

The tutorial starts with a circle of radius r:

```text
x = r * cos(phi)
y = r * sin(phi)
```

This provides the top-view foundation for radial head construction. The formulas are explanatory algorithm examples, not a documented command language accepted by a released application. [web:23]

### 5.2 Radial modulation and ridges

The example modifies radius with a periodic cosine wave:

```text
radius(phi) = r * (1 + 0.075 * cos(10 * phi))
x = radius(phi) * cos(phi)
y = radius(phi) * sin(phi)
```

| Mechanism | Effect | Important distinction |
|---|---|---|
| Radius modulation | Moves the outline inward and outward around the circumference. | Procedural shape control. |
| Periodic wave | Creates repeated lobes/ridges around the head. | The tutorial uses ten cycles. |
| Example modulation amplitude | Radius ranges from 0.925r to 1.075r. | These values describe the example, not the full application’s allowable range. |
| Selected rim segments | Mark locations for later tentacle attachment. | Connects head generation to appendage generation. |

Source: detailed making-of article. [web:23]

### 5.3 Dome and underside shaping

| Feature | How it works | Status |
|---|---|---|
| Side-profile construction | Begin with a circular profile sampled by an angle running from 0 to pi. | Tutorial explanation of original geometry. |
| Symmetrical profile | Construct mirrored points on opposite sides of the central axis. | Tutorial. |
| Convex upper head | Retain the upper portion of a curved profile to make the dome. | Original geometry explained in tutorial. |
| Concave lower head | Flip the relevant coordinate after a threshold angle. | Tutorial uses pi/2. |
| Profile offset | Add an offset to keep reflected regions from simply overlapping. | Example uses r/2. |
| Smoothed transition | Smooth the fold/edge for a more pleasing shape and fewer shading artifacts. | Exact code is deferred to example source. |
| Three-dimensional extension | Expand/revolve the profile into a volumetric head. | Creator’s article and retrospective. |
| Surface normal calculation | Calculate normals used for shading and displacement. | Original implementation account. |

Sources: making-of and retrospective. The formulas demonstrate the design principles; they are not a complete production mesh specification. [web:23][web:37]

## 6. Attachment points and appendage organization

The head generator emits more than a visible surface: it also emits joints/connection points used to grow other structures. This makes the head a procedural scaffold for the rest of the creature. [web:29]

| Feature | Description | Limit |
|---|---|---|
| Connection-point emission | Record attachment locations while constructing the head. | Exact stored data structure is not published in the reviewed prose. |
| Rim-based tentacle sites | Select segments around the head as tentacle start locations. | Illustrated in the head tutorial. |
| Normal-directed emergence | A tentacle’s initial forward vector can follow the attachment surface normal. | Algorithm explanation. |
| Shared starting infrastructure | Tentacles and hair are generated from connection points. | Original project description. |
| Feature-count controls | Number of generated features is parameterized. | No exhaustive field names or integer ranges supplied. |
| Feature-length controls | Appendage lengths are parameterized. | No complete per-appendage schema established. |
| Head/appendage coordination | Changes to the head and its joints feed later generation steps. | Interpretation of the documented pipeline. |

Sources: making-of and original project page. This does not establish skeletal rigging, skin weights, a general node editor, or user-authored attachment painting. [web:23][web:29]

## 7. Tentacle mesh generation

### 7.1 Curve-to-tube construction

The described problem is to build a tube-like mesh around a curve or polyline. The implementation propagates a local coordinate frame along that path and uses it to generate triangles. [web:23]

| Capability | Detail | Evidence class |
|---|---|---|
| Polyline-based centerline | Use successive points/segments as the backbone of a tentacle. | Original algorithm explanation. |
| Forward vector | Align the frame with the curve tangent or initial attachment normal. | Original explanation. |
| Up vector | Begin with a chosen up direction, illustrated as (0,1,0). | Tutorial. |
| Left vector | Calculate a perpendicular direction with a cross product. | Tutorial. |
| Frame propagation | Update orientation as the path bends. | Original algorithm explanation. |
| Surface triangles | Build the visible tube mesh around the local frames. | Original explanation. |
| Tapering | Reduce the relevant cross-section direction toward the tip. | Explicit tutorial example. |
| Curvature variation | Vary tentacle curvature to change creature morphology. | Portfolio parameter example. |
| Tip-weighted bending | Increase bending influence toward the end of the appendage. | Tutorial example. |
| Mouse-driven bending | Use mouse position to bend an example tentacle. | Tutorial only; not verified as a native application interaction. |
| Bending diagnostics | Show red lines indicating the example’s bending force. | Tutorial only. |

Sources: making-of and portfolio. [web:23][web:28]

### 7.2 Frame formulas and implementation boundary

The article illustrates:

```text
L = U cross F
U_next = F_next cross L
```

It describes this as borrowing from Frenet–Serret ideas without extensive calculus. The author also points Cinder users to an existing parallel-transport-frame implementation by another developer. That recommendation is not evidence that the original Cindermedusae program itself used that implementation. [web:23]

### 7.3 Head/appendage joins

The article’s joining explanation relies on shading to conceal surface discontinuities. It does not establish a watertight, Boolean-unioned, fabrication-ready mesh. Likewise, visual continuity is not evidence of one manifold connected topology. [web:23]

## 8. Hair and subsidiary structures

| Item | Established capability | What remains unknown |
|---|---|---|
| Loose hair | Creator identifies loose hair as one of the creature’s main parts. | Complete geometry construction and animation formulas. |
| Hair attachment | Head-generated joints are used to begin hair generation. | Placement distribution and exact count controls. |
| Feature variability | Length and number of features can vary. | Whether each parameter independently controls hair versus tentacles. |
| Integrated morphology | Hair contributes to the organism’s overall appearance. | Dedicated hair editor, strand solver, grooming, or collision system. |

Sources: original project page and retrospective. Do not substitute the documented tentacle algorithm for an unverified detailed hair implementation. [web:29][web:37]

## 9. Parameter system and authoring GUI

| Feature | Detailed behavior | Qualification |
|---|---|---|
| Custom parameter GUI | The creator built a simple graphical interface exposing the parameters. | Original. |
| Interactive shape exploration | Change values and observe the resulting shape. | Original. |
| Range discovery | Explore minimum and maximum values that produce useful creatures. | Original. |
| Constrained randomization | Choose random values within the selected sensible ranges. | Original; ranges are artist-selected, not a universal validity proof. |
| Head-radius parameter | Radius is explicitly named as a morphology variable. | Portfolio. |
| Tentacle-curvature parameter | Curvature is explicitly named as a variable. | Portfolio. |
| Feature-length parameter | Length is explicitly described as variable. | Original project page. |
| Feature-number parameter | Number of features is explicitly described as variable. | Original project page. |
| Continuous parameter values | Creator describes parameters as continuous and animatable. | Retrospective; count-like parameters still have discrete implications. |
| Interconnected parameter system | The design depends on relationships between controls, not just independent random parts. | Retrospective. |
| Time-varying settings | Morphological parameters can change over time. | Multiple primary descriptions. |
| Smooth parameter transitions | Parameter animation can transform one species-like appearance into another. | Portfolio. |

Sources: making-of, original page, portfolio, and retrospective. No complete GUI screenshot audit, exact widget inventory, preset browser, save-state format, keyframe editor, random-seed control, or automation API was established. [web:23][web:29][web:28][web:37]

## 10. Motion and animation

### 10.1 Normal-based head displacement

The making-of describes calculating positions and surface normals each frame, then moving points along their normals with a sine function:

```text
x += normal.x * sin(t + y * 0.5)
y += normal.y * sin(t + y * 0.5)
```

This excerpt explains a side-view example. The original project is three-dimensional, but the excerpt should not be silently represented as the complete 3D deformation shader or final source. [web:23]

| Feature | Visible or functional result | Qualification |
|---|---|---|
| Animation enable/disable | Displacement occurs when animation is enabled. | Original account; exact UI switch unspecified. |
| Periodic displacement | Repeated inward/outward movement of vertices. | Sine-based rather than a fluid simulation. |
| Normal-aligned movement | Moves points relative to the local surface direction. | Connects shape geometry to deformation. |
| Height-dependent phase | Add a vertical-coordinate contribution to time. | Example uses y * 0.5. |
| Wobbling wave | Different heights move out of phase rather than all pulsating together. | Explicit explanation. |
| Morphological animation | Animate shape-generating parameters, not just an already fixed mesh. | Original and portfolio. |
| Between-form transformation | Continuously evolve into another fictive species. | Portfolio. |
| GPU-animated variant | Original project page explicitly labels a “New version animated on the GPU.” | Later demonstration; code and benchmark not inspected. |

Sources: making-of, project page, and portfolio. “Looks, moves, and behaves differently” is an artistic description; the reviewed sources do not establish autonomous agents, learned behavior, ecological simulation, or neural control. [web:23][web:29][web:28]

## 11. Rendering architecture and visual goals

| Capability | Description | Boundary |
|---|---|---|
| Native graphics implementation | Original code is C++ using Cinder. | Not a ProcessingJS application. |
| OpenGL rendering | Used for rapid prototyping and high-resolution output. | No complete hardware compatibility matrix. |
| GLSL procedural shading | Shader techniques implement visual treatments including hatching. | No complete shader source audited here. |
| Diffuse-lighting inspection | Start with conventional diffuse lighting to check mesh quality and normals. | Development/debugging stage. |
| Natural-history illustration | Aim for an old encyclopedic plate rather than a photorealistic animal. | Final visual direction. |
| Haeckel-inspired aesthetics | Draw inspiration from Kunstformen der Natur. | Art reference, not a biological species database. |
| Dense final geometry | Use a higher-density mesh for smoother curves and fewer visible artifacts. | No exact vertex/triangle counts supplied. |
| Procedural surface effects | Produce the appearance without predefined texture assets, according to the creator. | Noise, texture coordinates, and procedural patterns still exist. |

Sources: making-of and project page. The creator experimented with subsurface scattering and obtained some results, but changed direction. Subsurface scattering should be catalogued as an explored approach, not established as an enabled final-style feature. [web:23][web:29]

## 12. Hatching and non-photorealistic shading

| Feature | Technical mechanism | Result |
|---|---|---|
| Procedural stripes | Generate vertical stripes along texture coordinates. | Basic sketch-line pattern. |
| Lighting-controlled density | Use diffuse lighting to select stripe density. | Darker areas receive denser black stripes. |
| Tonal illustration | Encode shading through line density rather than only smooth color gradients. | Natural-history/engraving-like appearance. |
| Stripe-width tuning | Adjust line width for a visually useful result. | Balances legibility and interference artifacts. |
| Moiré management | Consider stripe spacing, output size, and antialiasing together. | Mitigation, not a guarantee of complete elimination. |
| Offscreen rendering | Render through a large framebuffer object. | Supports print-oriented output. |
| Antialiasing | Use antialiasing to improve final appearance. | Exact algorithm/sample count not documented. |
| Derivative-dependent shading | Article discusses standard derivatives and dFdx/dFdy in explaining why this part lacks browser examples. | Historical browser limitation, not a statement about all modern browsers. |

The implementation is described as based on code in the OpenGL Shading Language Book. The article does not establish arbitrary uploaded hatching brushes, an illustration-style marketplace, multiple cross-hatching directions, or a user-editable shader graph. [web:23]

## 13. Five-layer image composition

The making-of explicitly describes five layers in each image. These are visual components of the final compositing process, not verified separately exportable layers in a PSD-like document. [web:23]

| Layer | Appearance | Purpose / operation |
|---|---|---|
| Yellow background | Warm paper-like field | Establishes the illustration’s ground. |
| Orange page-corner dirt | Weathered corner coloration | Adds a printed/handled-page feeling. |
| Black sketchy hatch | Dark line-based shading | Describes volume and tonal structure. |
| Blue highlights | Cool accent treatment | Adds selectively emphasized surface color. |
| Pink borders | Colored edge/border treatment | Completes the characteristic style. |

### Noise-masked coloration

Both the orange page corners and blue highlights are masked with noise so they appear crayon-like. The creator’s retrospective also describes the style in terms of ink, chalk, and crayon-like textures. These are descriptions of the visual rendering, not evidence of simulated pigment physics. [web:23][web:37]

### What cannot be inferred

The reviewed sources do not establish editable layer blend modes, arbitrary layer counts, color-management profiles, CMYK export, physically modeled paper, or a general-purpose painting system. Nor is it established that “pink borders” means an independently configurable outline pass with a public parameter list.

## 14. Composition and page layout

The original project page calls layout one of the hardest problems: random generation makes an organism’s shape, size, and position difficult to predict. The creator says transformations and iterative algorithms were used to manage page composition. [web:29]

| Feature | Documented role | Detail not supplied |
|---|---|---|
| Automatic layout handling | Accommodate randomly generated morphology on a page. | Complete objective function. |
| Transform-based adjustment | Modify placement/scale/orientation through transformations. | Which exact transform sequence is used. |
| Iterative adjustment | Refine the result algorithmically rather than relying on a single fixed placement. | Stopping conditions, iteration count, and collision tests. |
| Print-oriented composition | Produce finished illustration pages, not only isolated mesh previews. | Exact margin controls and trim/bleed behavior. |
| Variable creature bounds | Handle changes in silhouette caused by parameter randomization. | A formal bounding-box guarantee is not given. |

Source: original project page. It is reasonable to interpret this as composition automation, but not to invent a packing solver, camera optimizer, typography engine, or guaranteed no-cropping algorithm. [web:29]

## 15. Resolution, image generation, and performance

| Reported figure | Source context | Correct interpretation |
|---|---|---|
| 4080 × 2720 pixels | Making-of: large offscreen FBO used with antialiasing. | A specific documented rendering-buffer size. |
| Approximately 4000 × 3000 pixels | Original project page describes high-resolution animated pictures. | A broader high-resolution claim, not necessarily the same render configuration. |
| Around 10 fps | Making-of: animation speed at the time of writing. | Historical observation on unspecified hardware/settings. |
| Near-realtime | Original project page and contemporary coverage. | Qualitative description; not guaranteed 30/60 fps. |
| 15-second maximum calculation time | Independent coverage describes Written Images submission requirements. | Project-context requirement, not a measured Cindermedusae benchmark. |
| GPU animation | Later variant labeled on original project page. | Confirms a development direction was demonstrated, not its achieved frame rate. |

Sources: creator’s article/project page and Syntopia’s contemporary Written Images coverage. These statements concern different moments and configurations; do not merge them into a claim that all features run at 10 fps at 4080 × 2720 on any current machine. [web:23][web:29][web:24]

### Output boundaries

The sources establish generated images, printed artwork, and animated presentations. They do not establish the program’s exact supported image file extensions, native project format, video encoder, command-line batch interface, multi-layer image export, or mesh export support. Print publication is not proof of native PDF output. [web:29][web:28]

## 16. Explanatory browser sketches

The making-of uses ProcessingJS examples to explain concepts implemented originally in C++/Cinder. Most examples are two-dimensional and interactive; selected three-dimensional examples require WebGL. [web:23]

| Example | Concept demonstrated | Capability boundary |
|---|---|---|
| Head from above | Circular sampling, radial modulation, attachment sites. | Teaching sketch, not full generator. |
| Head from the side | Convex top, concave underside, edge shaping. | Simplified geometric explanation. |
| Animated side view | Normal displacement and phase-shifted wobble. | Does not expose all production controls. |
| 3D head | Combine head-building steps in three dimensions. | Creator says the illustrative version is not optimized. |
| Tentacle mesh | Build a tube around a path with taper and interactive bending. | Mouse interaction belongs to this example. |
| Head with tentacles | Combine the head and appendages. | Not a verified complete downloadable authoring environment. |

### Historical browser caveats

The author reported poor performance for the simplified 3D example and did not provide ProcessingJS versions of the final shading because of the GLSL derivative support available at the time. These are historical statements from a 2010 article. They do not by themselves prove that the same limitation applies to modern WebGL, nor that the old examples still execute unchanged today. [web:23]

## 17. Later variants and exhibition use

| Variant / setting | What is explicitly documented | What is not established |
|---|---|---|
| GPU-animated version | Project page labels a newer animation example as GPU-animated. | Release date, code, supported cards, fps. |
| Interactive exhibition | Interactive version at Computational Aesthetics ’11 in Vancouver. | Input devices, full control mapping, installation instructions. |
| Generative-book publication | Included in Written Images, whose copies contain unique generated imagery. | Exact publishing integration/API. |
| Toronto public art | Displayed in Toronto Metro stations during October 2013, Drift:Synthesis. | Live generation versus playback pipeline for every display. |
| Exhibition history | Portfolio lists Computational Aesthetics, Moscow Biennale, Artist, reveal yourself!, and Drift:Synthesis. | A separate software feature for every venue. |
| Projection/material experimentation | Original page labels a set of experiments with projections and materials. | A documented projection-mapping editor or material browser. |

Sources: original project page and Variable portfolio. Exhibition history demonstrates applications of the artwork, not broad commercial product support. [web:29][web:28]

## 18. Unity port and other related coverage

### 18.1 Indexed Unity implementation

Search results identify the public repository `IxxyXR/Cindermedusae`, described as “Marcin Ignac’s procedural sea creature project ported to Unity 3D.” This establishes that a separately attributed Unity port is indexed. [web:27]

Attempts to retrieve its repository and README content did not succeed during this research. Therefore this inventory does not attribute any of the following to that port:

- Exact Unity version requirements.
- Shader/render-pipeline compatibility.
- Supported morphology parameters.
- GUI, randomization, animation, or export parity.
- VR support, despite the repository owner’s name.
- Licensing, maintenance status, build instructions, or executable availability.

The port is a discovery lead, not evidence that the original C++ application’s complete features work in Unity.

### 18.2 Independent contemporary descriptions

Syntopia’s October 2010 coverage independently describes Cindermedusae as a Cinder/OpenGL work producing imaginary sea creatures in Haeckel’s style, and places it in Written Images’ near-realtime generative context. [web:24]

CreativeApplications has an indexed October 2010 article describing the project as a generative encyclopedia of imaginary sea creatures selected for Written Images. Its full page could not be retrieved, so its search excerpt is used only as corroborating context, not as a source for detailed hidden features. [web:32]

Additional indexed pages often repeat the creator’s description or offer short aesthetic commentary. They should not be counted as independent evidence for features absent from the primary sources.

## 19. Implemented, explored, and proposed features

| Item | Evidence status | Reason |
|---|---|---|
| Procedural head/tentacles/hair | Implemented | Explicit original algorithm description. |
| Parameter GUI | Implemented | Explicit making-of account. |
| Randomized parameters | Implemented | Multiple primary descriptions. |
| Animated parameters and wobble | Implemented | Algorithm account and portfolio. |
| Five-layer illustrative rendering | Implemented | Detailed making-of. |
| High-resolution offscreen rendering | Implemented | Specific FBO size reported. |
| Automatic/iterative page layout | Implemented, incompletely specified | Explicit project description. |
| Interactive exhibition | Demonstrated later | Variable portfolio. |
| GPU animation | Demonstrated later | Project-page label. |
| Subsurface scattering | Explored | Creator experimented, then changed the visual direction. |
| Full online creature creator | Proposed in making-of | A contemplated WebGL port is not proof of a released full application. |
| Better animated performance | Proposed in making-of | Later GPU work exists, but no verified final performance specification. |
| Different organism types | Proposed | Creator describes future expansion. |
| Plant generation | Proposed | Mentioned as a possible extension, not verified shipped functionality. |
| Unity implementation | Separately indexed | Repository description establishes a port, not feature parity. |

Sources: making-of, project page, portfolio, and indexed repository. The browser teaching sketches are real examples, but they do not by themselves satisfy the proposed full online-creator feature. [web:23][web:29][web:28][web:27]

## 20. Reconstructed end-to-end pipeline

The following is a synthesis of the documented mechanisms, not copied production source and not a guaranteed exact execution order for every variant.

```text
Choose or animate morphology parameters
    |
    v
Generate sphere-derived head
    |-- radial modulation
    |-- convex/concave profile
    |-- smoothing and normals
    |-- connection points
    |
    v
Generate appendages
    |-- tentacle centerlines and local frames
    |-- tapered tube meshes
    |-- hair from generated joints
    |
    v
Apply motion / deformation when enabled
    |-- normal displacement
    |-- time-dependent phase shifts
    |-- parameter-space transitions
    |
    v
Manage page composition
    |-- transformations
    |-- iterative layout adjustment
    |
    v
Render visual components
    |-- diffuse-light-driven hatch
    |-- color accents and noise masks
    |-- background / page treatment
    |
    v
Composite high-resolution illustrated output
```

The relationship between form and rendering is crucial: the 3D structure supplies normals and silhouette, while the non-photorealistic shading turns that structure into an encyclopedia-like image. The parameter system generates variety, and the layout stage makes that variety usable on a printed page. [web:23][web:29][web:28]

## 21. Practical workflows supported by the evidence

### A. Generate a new illustrated creature

1. Explore morphology using the custom parameter GUI.
2. Select visually useful parameter ranges.
3. Choose values manually or randomize them.
4. Generate the head and attachment sites.
5. Generate appendages and compose the result.
6. Render the layered illustrative image at high resolution.

This is a reconstruction from the creator’s descriptions, not a verified menu-by-menu user manual. [web:23][web:29]

### B. Animate a creature or species transition

1. Start from a parameterized form.
2. Enable periodic mesh displacement for wobble.
3. Vary continuous morphology parameters over time.
4. Present the result as animation or an interactive installation.

The evidence supports these mechanisms, but does not establish a keyframe timeline, video-export menu, or reusable animation-file format. [web:23][web:28][web:37]

### C. Study or recreate the geometry

1. Begin with the top-view circle and its radius modulation.
2. Construct a domed, concave-bottomed profile.
3. Extend the construction into 3D.
4. Record attachment sites and normals.
5. Sweep/tessellate tentacle geometry along paths.
6. Add taper and bending.
7. Apply normals, lighting, and the illustrative shader treatment.

The article supplies a conceptual scaffold and links explanatory examples. It is not, by itself, a complete production source distribution. [web:23]

### D. Adapt the idea to another graphics engine

The documented decomposition into a head, attachment points, curve-based appendages, parameters, and shader layers offers a clear conceptual porting strategy. However, engine-specific implementation, asset serialization, rendering compatibility, and feature parity remain separate engineering tasks. The indexed Unity port is evidence that such a port exists, not that it solves all these tasks for every current Unity version. [web:23][web:29][web:27]

## 22. Limitations and capabilities not established

The following should not be presented as verified features of the original program on the basis of this research:

### Distribution and productization

- A currently maintained installer or downloadable end-user edition.
- A complete open-source release of the original C++ project.
- A known current license for the original implementation.
- A supported operating-system/hardware matrix.
- Versioned release notes or a commercial support policy.
- A complete public parameter reference or operator manual.

### Modeling and animation

- General mesh sculpting, Boolean modeling, retopology, or skeletal rigging.
- Verified watertight/manifold output.
- Collision-aware appendages or self-collision prevention.
- Fluid simulation, buoyancy, tissue mechanics, or biological accuracy.
- An autonomous behavior, genetic-algorithm, breeding, or natural-selection simulator.
- Preset storage, deterministic seeds, undo/redo, autosave, or a keyframe editor.
- Arbitrary animal/plant generators merely because future extensions were discussed.

### Rendering and data exchange

- Native SVG/PDF/PSD output or separately exportable compositing passes.
- OBJ/STL/FBX/glTF mesh export.
- A documented video encoder or image-sequence exporter.
- CMYK/ICC print color management.
- Ray tracing, path tracing, physically based materials, or production subsurface scattering.
- A public scripting/plugin API, command-line interface, or cloud batch service.

### Related implementations

- Full feature parity between the C++ original, ProcessingJS examples, GPU variant, and Unity port.
- A released full-feature WebGL creature-creation application.
- A claim that old browser examples still run in all current browsers.
- Native VR support inferred from a repository owner’s name.

These are evidence gaps, not definitive statements that a capability cannot exist. The original project is documented chiefly as an artwork and technical experiment, so it should not be evaluated as though it came with a modern commercial product specification.

## 23. Requirements-style feature checklist

This checklist summarizes what could reasonably be included in a faithful reconstruction. It is not a list of verified existing UI buttons.

### Geometry

- [x] Sphere-derived, radially modulated head.
- [x] Convex upper and concave lower profile.
- [x] Smoothed transition regions.
- [x] Surface normal calculation.
- [x] Head-generated attachment points.
- [x] Procedural tentacle meshes.
- [x] Taper and curvature variation.
- [x] Procedural hair attachments.
- [ ] Complete published head/tentacle/hair parameter schema.
- [ ] Verified manifold surface union and fabrication export.

### Authoring and variation

- [x] Custom parameter GUI.
- [x] Artist-selected useful parameter ranges.
- [x] Randomized morphology.
- [x] Animatable parameter system.
- [x] Continuous species-like transitions.
- [ ] Verified random-seed persistence.
- [ ] Verified preset/project save and reload.

### Animation

- [x] Normal-based periodic displacement.
- [x] Height-dependent phase shift.
- [x] Wobbling head motion.
- [x] Later GPU-animation demonstration.
- [ ] Verified physically simulated jellyfish propulsion.
- [ ] Verified public animation editing/export interface.

### Style and output

- [x] Diffuse-light-controlled hatch density.
- [x] Five-part illustrated composition.
- [x] Noise-masked page-corner/highlight treatment.
- [x] High-resolution offscreen rendering.
- [x] Antialiasing considerations.
- [x] Iterative composition/layout handling.
- [ ] Verified modern image/mesh format matrix.
- [ ] Verified native vector or layered-document export.

Each checked item is grounded in the documented mechanisms, not runtime testing. [web:23][web:29][web:28][web:37]

## 24. Source map and research notes

| Source | Contribution | Evidence quality |
|---|---|---|
| [web:23] Making Generative Creatures | Most detailed algorithm, GUI, animation, shading, resolution, and future-plan descriptions. | Primary source; historical implementation account. |
| [web:29] Original project page | Procedural head/joints/appendages, no predefined assets, composition algorithms, high-resolution claims, later GPU label. | Primary source. |
| [web:28] Variable portfolio | Explicit parameter examples, smooth species transformations, publication and interactive/public-art history. | Primary studio account. |
| [web:37] From Abstraction to Realism and Back | Retrospective decomposition, interconnected continuous parameters, design reasoning. | Primary reflective account, not an API manual. |
| [web:24] Syntopia: Written Images | Independent contemporary context, Cinder/OpenGL and near-realtime characterization, submission-time requirement. | Secondary source. |
| [web:32] CreativeApplications article | Contemporary project identification and publication context. | Search excerpt only; full retrieval failed. |
| [web:27] IxxyXR/Cindermedusae | Indexed description of a Unity 3D port. | Search excerpt only; repository/README retrieval failed. |

### Primary source locations

- Requested making-of article: <http://marcinignac.com/blog/cindermedusae-making-generative-creatures/>
- Creator’s project page: <http://marcinignac.com/projects/cindermedusae/>
- Variable portfolio: <https://variable.io/cindermedusae/>
- Creator’s retrospective: <http://marcinignac.com/blog/from-abstraction-to-realism-and-back/>

### Additional source locations

- Syntopia’s contemporary Written Images article: <http://blog.hvidtfeldts.net/index.php/2010/10/written-images/>
- CreativeApplications coverage: <https://www.creativeapplications.net/project/cindermedusae-cinder/>
- Indexed Unity port: <https://github.com/IxxyXR/Cindermedusae>

### Research transparency

The first four sources were read as page-level text, as was Syntopia’s article. The Unity repository and CreativeApplications page were discovered through search, but page retrieval failed. No detailed capabilities are attributed to their unseen contents. Browser-example execution, video-frame analysis, repository-code auditing, and original executable testing were outside the completed evidence base.

No numerical benchmark was calculated from screenshots or inferred from video. Reported performance and resolution figures remain attributed to their original contexts. Historical plans are not silently promoted into completed features, and tutorials are not silently promoted into a released browser application.

---

Prepared as an original, source-supported feature synthesis. The citations identify evidence used in the conversation; the source-location list keeps the Markdown independently useful after download.
