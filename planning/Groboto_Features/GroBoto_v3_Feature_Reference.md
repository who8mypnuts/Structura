# GroBoto v3 --- Comprehensive Feature Reference

**Product:** GroBoto 3.x\
**Developer:** Braid Art Labs\
**Product type:** Procedural / generative 3D modeling, organic art,
rendering, and animation\
**Historical release period:** GroBoto 3.0 appeared for macOS in
February 2011; the Windows release followed in 2011. A later 3.2 update
added further export/grouping capabilities.

------------------------------------------------------------------------

## About this document

This reference consolidates the GroBoto v3 capabilities that can be
substantiated from surviving product announcements, contemporary
reviews, and workflow documentation.

To avoid mixing versions together:

-   **GroBoto 3.0 additions** identifies capabilities specifically
    promoted as new in version 3.
-   **Inherited GroBoto capabilities** covers earlier features that were
    still present in v3. The v3 announcement explicitly says that the v2
    algorithmic creation tools remained.
-   **GroBoto 3.2 additions** identifies later v3.x capabilities
    documented in the GroBoto-to-modo workflow guide.
-   **Workflow observations** records practical interface details and
    limitations described by a contemporary v3 review.

Some surviving documentation is incomplete. This is therefore a broad,
source-backed feature inventory, not a claim that every menu item or
parameter in the original application has been recovered.

------------------------------------------------------------------------

# 1. Core concept and generative approach

GroBoto is not primarily a conventional polygon modeler. It uses
procedural, true-geometry objects and algorithmic systems called
**Bots** to help artists grow complex forms from simpler elements.

Its characteristic workflow combines:

-   Algorithmic generation of organic, abstract, mechanical,
    architectural, and science-fiction-inspired forms.
-   Interactive exploration of three-dimensional shapes.
-   Procedural geometry that remains editable before export.
-   Bot behaviors and drawing shapes that can be adjusted in real time.
-   Combination of automatically generated structures with manually
    placed and transformed geometry.
-   A rendered working environment intended to make modeling feel
    immediate and visual rather than technical.
-   Conversion of procedural geometry into polygon meshes for use in
    other 3D applications.

The application was designed around exploration: the artist establishes
or selects a generative starting point, adjusts its behavior and
geometry, and develops the resulting form through direct interaction.

# 2. Bots and procedural generation

Bots are GroBoto's signature algorithmic drawing and modeling systems.
They generate geometric structures and can be adjusted to produce many
different results.

## 2.1 Bot creation and editing

-   Library of predefined Bots and Bot presets.
-   Multiple algorithmic Bot types for generating different kinds of
    structures.
-   Real-time editing of Bot behavior.
-   Adjustable drawing shapes.
-   Adjustable source-object geometry.
-   Bot-specific parameters and global Bot settings.
-   Ability to create and save user-defined Bot variations.
-   Ability to reuse saved Bot variations.
-   Bot objects can be added to a scene from the library.
-   Existing Bots can be selected and further edited.
-   Bot geometry can be twisted, skewed, and scaled.
-   Textures can be applied to or removed from Bots.
-   Bot generation can be combined with scene-level object editing.
-   Scene Bots and reusable Bots are represented separately in the
    library.

## 2.2 Bot object generation

-   Control over the objects used by a Bot to construct its generated
    form.
-   Object alignment options controlling how source objects sit along
    Bot branches.
-   Use of different object types as Bot source geometry.
-   **Strip mode:** define an arbitrary sequence of source objects of
    different types, rather than being limited to two source objects.
-   Repeated and varied source geometry for more complex generated
    structures.

## 2.3 Bot libraries and presets

The v3 interface review identifies these library categories:

-   Scene Bots
-   Scene Textures
-   Bots
-   Maps
-   Primitives
-   Textures

Library items can be selected and dragged into the scene for further
editing.

## 2.4 Generative structure and artistic uses

Documented Bot behavior supports the creation of:

-   Organic forms.
-   Abstract forms.
-   Architectural forms.
-   Complex recursive and procedural structures.
-   Elaborate decorative or sculptural objects.
-   Fantasy and science-fiction models and scenes.

The exact internal algorithm names and the complete list of Bot types
are not consistently available in surviving public documentation, so
this reference does not invent a full Bot taxonomy.

# 3. Object placement, transformation, and scene editing

GroBoto combines generative construction with direct manipulation of
scene objects.

## 3.1 Basic transforms

-   Select objects in the scene.
-   Move objects along the X, Y, and Z axes.
-   Rotate objects.
-   Scale objects.
-   Twist and skew Bot geometry.
-   Duplicate objects.
-   Transform objects using their geometric properties and
    relationships.
-   Align objects to other objects.
-   Snap and align objects using intelligent placement options.

## 3.2 Relational and group editing

-   Group objects.
-   Reshape objects.
-   Align objects to the surfaces of other objects.
-   Edit object relationships interactively.
-   Use object relationships and geometric properties to guide
    placement.
-   Lock or unlock selection.
-   Select and manipulate groups of scene elements.

## 3.3 Flex tools --- v3

GroBoto 3 introduced **Flex Tools** for applying broad,
range-of-influence edits to complex arrangements of primitives and
Boolean geometry.

Their purpose is to let an artist influence a region or collection of
geometry without having to manipulate every primitive independently.

The v3 announcement describes these tools in terms of broad influence
over complex primitive-and-Boolean arrangements; surviving sources do
not provide a complete inventory of individual Flex tool modes.

# 4. Primitive-based modeling and Boolean operations --- v3

GroBoto 3 significantly expanded the application from generative organic
art into more general-purpose geometric modeling.

## 4.1 True geometric primitives

-   Use editable geometric primitives as modeling elements.
-   Work with true geometric primitives rather than treating every
    element as a polygon mesh.
-   Combine primitives into complex arrangements.
-   Continue editing the underlying geometry before mesh generation.
-   Use primitive properties and relationships for intelligent snapping,
    alignment, duplication, and transformation.

## 4.2 Boolean modeling

-   Real-time Boolean modeling.
-   Real-time Boolean editing.
-   Boolean combinations of geometric primitives.
-   Complex arrangements of primitives and Boolean operations.
-   Tracking of Boolean intersections and trims.
-   Precision handling of intersection boundaries.
-   Use of Boolean operations to create complex forms from simpler
    solids.

The v3 announcement emphasizes that the Boolean workflow operates on
true geometry, not merely on polygon meshes.

## 4.3 Smoothing and stylization

-   Automatically generate meshes from complex primitive and Boolean
    arrangements.
-   Smooth generated meshes.
-   Stylize generated meshes.
-   Produce high-fidelity surfaces from complex geometric constructions.

# 5. Automatic mesh generation --- v3

Automatic mesh creation is one of the defining v3 additions.

## 5.1 Unified mesh shells

-   Fully automatic polygon mesh generation from GroBoto geometry.
-   Combine all scene geometry into a single unified mesh shell.
-   Alternatively, generate a mesh from any selected subset of the
    geometry.
-   Convert complex primitive and Boolean arrangements into polygonal
    output.
-   Preserve Boolean trims and intersections during mesh creation.

## 5.2 SeamNet

GroBoto's mesh-generation technology converts tracked Boolean trims and
intersections into a structured mesh system called **SeamNet**.

Documented characteristics include:

-   Precision tracking of Boolean seams and intersections.
-   Conversion of those boundaries into structured mesh topology.
-   Multi-row edge loops around precision seams.
-   Mesh structure designed to be useful for downstream modeling and
    texturing.
-   Seam information retained in OBJ export.

## 5.3 Mesh density

-   Global mesh-density control.
-   Local mesh-density control.
-   Procedural regeneration of meshes at different densities.
-   Ability to regenerate geometry at a different resolution without
    rebuilding the original model manually.

The procedural source geometry is important: it allows the mesh to be
regenerated at a chosen density rather than forcing the artist to work
with one fixed polygon resolution.

# 6. OBJ export and downstream modeling

GroBoto v3 was designed to make its generated geometry useful in other
3D applications.

## 6.1 OBJ geometry export

-   Export polygon meshes in OBJ format.
-   Export meshes generated from GroBoto's procedural geometry.
-   Choose polygon resolution through mesh-density controls.
-   Export unified mesh shells.
-   Export selected subsets of scene geometry.
-   Export precision seam topology.
-   Include multi-row edge loops around seams.
-   Include special UV data intended to help select, mask, or manipulate
    structured model elements in other 3D applications.
-   Export options for grouping and tessellation.

## 6.2 v3.2 group-based export features

A GroBoto-to-modo Toolkit guide documents features requiring **GroBoto
v3.2**:

-   Assign primitives and Boolean clusters to named GroBoto Groups.
-   Configure seam and map export settings for each group.
-   Export separate meshes for each GroBoto Group.
-   Add GroBoto Group-based material tags to OBJ output.
-   Export bitmap texture maps separately for each group.
-   Group geometry by patch during export.
-   Export vertex-map information as OBJ normals.
-   Use group/material information to separate imported geometry in
    modo.

These are useful pipeline features for transferring complex GroBoto
models into another 3D package while retaining meaningful divisions in
the source model.

## 6.3 GroBoto-to-modo workflow support

The third-party GroBoto-to-modo Toolkit documents a downstream workflow
involving:

-   Preparing imported GroBoto meshes.
-   Separating meshes based on GroBoto Groups.
-   Creating shader groups corresponding to material-tagged groups.
-   Using GroBoto patch information as modo parts.
-   Generating selections from seam rows.
-   Creating vertex weight maps around seams.
-   Using seam-aware weights to support further modeling operations.

The toolkit is a separate set of scripts/configuration for modo, not a
built-in GroBoto feature. Its documentation is nevertheless useful
evidence of the structure and data exposed by GroBoto's OBJ export.

# 7. Textures, maps, and materials

GroBoto includes a procedural texture workflow and a library of reusable
texture assets.

## 7.1 Texture creation and management

-   Built-in texture library.
-   User Library Textures for user-created textures.
-   Create new textures.
-   Modify existing textures.
-   Assign textures to selected objects and Bots.
-   Apply and remove textures from Bot geometry.
-   Scene texture library.
-   Texture options panel for adjusting selected textures.

## 7.2 Conformal texture mapping

GroBoto's proprietary conformal texture-mapping technology was designed
to apply textures to complex smooth geometry without the distortion
associated with conventional projection approaches.

Documented capabilities include:

-   Conformal texture mapping.
-   Artifact-resistant texture mapping.
-   Texture application without requiring the artist to define
    conventional UV mapping or projection schemes.
-   Seamless, patternless tiled textures.
-   Build tiled textures from TIFF image files.

## 7.3 Texture controls

-   Texture tiling.
-   Directional texture tiling.
-   Color maps.
-   Bump maps.
-   Bump effects.
-   Specular highlights.
-   Self-illumination.
-   Texture-level illumination controls.
-   Texture editing and adjustment.

## 7.4 Directional texture tiling --- v2.1 feature carried into v3

Directional tiling supports textures whose patterns have a preferred
direction. The original announcement gives tree bark as an example of a
texture that benefits from directional rather than purely uniform
tiling.

## 7.5 Self-illuminating materials

-   Self-illuminating textures.
-   Self-illuminating objects.
-   Independent illumination effects at the texture and object levels.

# 8. Lighting and shadows

GroBoto provides scene lighting controls and rendered feedback while
editing.

-   Multiple light sources.
-   Local lights.
-   Cast shadows.
-   Shadow opacity control.
-   Shadow temperature control.
-   Object self-illumination.
-   Texture self-illumination.
-   Light options panel.
-   Real-time lighting and shadow feedback in the rendered workspace.

# 9. Environment, backgrounds, and atmospherics

## 9.1 Fog

-   Layered fog atmospherics.
-   Fog color control.
-   Fog thickness control.
-   Fog altitude control.
-   Fog transparency control.

## 9.2 Sky and background

-   Sky gradients.
-   Interactive sky color controls.
-   Sky transition-angle control.
-   Background color controls.
-   Scene presets.

## 9.3 Star fields

-   Procedural star-field generation.
-   Star count control.
-   Star cluster controls.

These environment features were introduced in GroBoto 2.1 and are part
of the inherited feature set relevant to v3.

# 10. Rendering and display

GroBoto emphasizes a fully rendered interactive workspace.

## 10.1 Interactive display

-   Fully rendered modeling workspace.
-   Real-time editing with rendered feedback.
-   Real-time Bot editing.
-   Antialiased display.
-   Textures visible during interactive editing.
-   Cast shadows visible during interactive editing.
-   Responsive camera and AutoBot editing supported by interruptible
    rendering.
-   Improved rendering speed in the 2.1 update.

## 10.2 Rendering quality and geometry

-   Smooth-shape rendering.
-   Smooth-surface rendering at different scales.
-   High-resolution image output.
-   Procedural geometry retained until export, avoiding the need to
    commit to a fixed polygon mesh during ordinary scene work.

## 10.3 Display and rendering modes

Documented display/rendering capabilities include:

-   Fully rendered display.
-   Polygon display mode.
-   Tessellation options for polygon display.
-   Graphical line rendering mode.
-   Outline rendering mode.
-   Antialiasing.
-   Cast-shadow display.

## 10.4 Render interruption

The 2.1 update introduced interruptible rendering to make camera and
AutoBot editing more responsive.

# 11. Image filters and color controls

The 2.1 update added inline color filters:

-   Brightness.
-   Contrast.
-   Saturation.
-   Hue.

These controls are intended for direct image/color adjustment within the
GroBoto workflow.

# 12. Animation

GroBoto includes a specialized animation system called **Kinetic
Morphing**.

## 12.1 Kinetic Morphing

-   Morph from one AutoBot configuration to another.
-   Generate fluid motion from a relatively small number of Bot
    keyframes/configurations.
-   Arrange AutoBots in an Animation Strip.
-   Preview the resulting animation.
-   Adjust sequencing and movement through Morph settings.
-   Animate changes in object position.
-   Animate camera changes.
-   Animate lighting changes.
-   Animate background color changes.
-   Use morphing kinetics to produce more complex motion.

## 12.2 Animation workflow

A contemporary v3 review describes a basic workflow:

1.  Select an AutoBot.
2.  Place it in the Animation Strip.
3.  Select another AutoBot.
4.  Place the second AutoBot in the strip.
5.  Preview the animation.
6.  Adjust sequencing and movement in the Morph controls.

## 12.3 Animation limitations documented by a contemporary review

-   Kinetic Morphing is the animation approach described by the
    reviewer.
-   Not all Bot types are available for animation.
-   Animation therefore depends on choosing compatible Bot types.
-   The workflow differs from a conventional general-purpose timeline
    where arbitrary object properties can be keyed freely.

The original product announcement describes Kinetic Morphing as
automatically generating sophisticated motion from a few Bot keyframes.
The review supplies the practical caveat that the available Bot types
are constrained.

# 13. Camera and scene navigation

The v3 interface review identifies a Camera section in the left-side
panel.

Documented controls and workflow include:

-   Move the camera.
-   Rotate the camera.
-   View the scene as a whole.
-   Zoom the camera.
-   Adjust camera views while composing a scene.

The review notes that camera and lighting adjustment could be cumbersome
for new users. It specifically wished for more convenient
three-mouse-button panning and zooming, so that should not be assumed to
be a native v3 capability.

# 14. User interface and workspace

A contemporary v3 review describes a multi-pane interface.

## 14.1 Central workspace

-   Main scene-composition area.
-   Fully rendered 3D viewport.
-   Direct object interaction.
-   Drag-and-drop placement of library objects.

## 14.2 Left pane

-   Library browser.
-   Scene Bots.
-   Scene Textures.
-   Bots.
-   Maps.
-   Primitives.
-   Textures.
-   Camera controls.

## 14.3 Right pane

The review identifies five major tabs:

-   **Selection & Group:** selection and grouping controls.
-   **Scene Options:** scene-level controls.
-   **Light Options:** lighting controls.
-   **Texture Options:** texture creation and adjustment.
-   **Bot Options:** Bot selection and parameters.

## 14.4 Bottom-center controls

-   Edit tab.
-   Animate tab.
-   Select.
-   Move.
-   Rotate.
-   Scale.
-   X, Y, and Z axis controls.
-   Camera zoom.
-   Lock Selection toggle.

## 14.5 Library workflow

-   Browse assets by category.
-   Select a library item.
-   Drag and drop the item into the scene.
-   Edit the inserted object or Bot using the relevant controls.

# 15. Still-image, sequence, and movie output

## 15.1 Still-image formats

Documented image output formats:

-   TIFF.
-   JPEG.
-   BMP (Windows/PC).

## 15.2 Movie output

Documented movie output:

-   AVI (Windows/PC).
-   QuickTime (Mac).

## 15.3 Image channels and alpha/depth output

GroBoto's documented rendering modes include:

-   RGB.
-   RGB + alpha.
-   Depth (Z).
-   Depth with unmultiplied RGB.
-   Depth-composite alpha with multiplied RGB.

The original product announcement specifically documents TIFF output for
still images and sequential image output in these modes.

## 15.4 Sequential output

-   Render sequential image frames.
-   Render animation/movie output.
-   Produce still and sequential output with alpha/depth options.

# 16. Version-specific feature history

This section helps separate features introduced at different points in
the product's development.

## 16.1 Original GroBoto capabilities (2006)

The original product announcement documents:

-   Algorithmic Bots for organic, abstract, and architectural forms.
-   Real-time adjustment of Bot behavior, drawing shapes, and textures.
-   Saving unlimited Bot variations.
-   Kinetic Morphing animation.
-   Relational object editing.
-   Object grouping and reshaping.
-   Alignment to other objects' surfaces.
-   Antialiased real-time rendered feedback.
-   Multiple light sources and cast shadows.
-   Conformal texture mapping.
-   Seamless tiled textures built from TIFF files.
-   OBJ export with grouping and tessellation options.
-   Procedural geometry export at a chosen polygon resolution.
-   Alpha and depth rendering modes.
-   Still-image and movie output.

## 16.2 GroBoto 2.1 capabilities carried into v3 (2007)

The 2.1 announcement documents:

-   Additional algorithmic Bots and Bot presets.
-   Expanded Bot object-generation controls.
-   Strip mode for arbitrary sequences of source objects.
-   Additional object-alignment options along Bot branches.
-   Directional texture tiling.
-   Self-illuminating textures.
-   Self-illuminating objects.
-   Layered fog with color, thickness, altitude, and transparency.
-   Sky gradients with color and transition-angle controls.
-   Star-field generation with count and cluster controls.
-   New morphing kinetics and improved morph animation.
-   Scene presets.
-   Interruptible rendering for camera and AutoBot editing.
-   New tessellation options for polygon display.
-   Inline brightness, contrast, saturation, and hue filters.
-   Shadow opacity and temperature controls.
-   Improved rendering speed.
-   User-interface enhancements.

## 16.3 GroBoto 3.0 additions (2011)

The v3 announcement specifically highlights:

-   Real-time Boolean modeling and editing.
-   True geometric primitives rather than mesh-based primitives.
-   Flex Tools with broad range-of-influence editing.
-   Intelligent snapping.
-   Intelligent alignment.
-   Intelligent duplication.
-   Intelligent transformation.
-   Fully automatic mesh generation.
-   Unified mesh shells.
-   Selection of all or a subset of scene geometry for meshing.
-   Precision tracking of Boolean trims and intersections.
-   SeamNet structured mesh generation.
-   Local and global mesh-density controls.
-   Automatic regeneration of meshes at different densities.
-   OBJ export with precision seams and multi-row edge loops.
-   Special UVs for selecting, masking, and manipulating structured
    model elements.

The v3 announcement explicitly states that GroBoto v2's algorithmic
creation tools remained in the product.

## 16.4 GroBoto 3.2 additions

The GroBoto-to-modo Toolkit documentation identifies v3.2 as adding or
supporting:

-   GroBoto Group-based material tags.
-   Separate mesh export for each GroBoto Group.
-   Group-specific seam and map export settings.
-   Separate bitmap output for each group.
-   Group-aware OBJ export workflows.

These capabilities are documented as v3.2 requirements in the toolkit
guide.

# 17. Consolidated feature checklist

A compact inventory for reference or planning:

### Generative systems

-   [x] Algorithmic Bots
-   [x] Bot presets
-   [x] Bot behavior editing
-   [x] Drawing-shape editing
-   [x] Source-object control
-   [x] User-defined Bot variations
-   [x] Strip mode
-   [x] Object alignment along Bot branches
-   [x] Scene Bot library

### Modeling and editing

-   [x] True geometric primitives
-   [x] Real-time Boolean operations
-   [x] Boolean trimming and intersections
-   [x] Flex Tools
-   [x] Move, rotate, and scale
-   [x] Twist and skew
-   [x] Duplicate
-   [x] Snap and align
-   [x] Group and reshape
-   [x] Relational editing

### Mesh generation

-   [x] Automatic mesh generation
-   [x] Unified mesh shells
-   [x] Mesh selected subsets
-   [x] SeamNet
-   [x] Precision seam topology
-   [x] Multi-row seam edge loops
-   [x] Local mesh density
-   [x] Global mesh density
-   [x] Smooth and stylize generated meshes

### Export and interoperability

-   [x] OBJ export
-   [x] Grouping options
-   [x] Tessellation options
-   [x] Precision seams in OBJ
-   [x] Special UV data
-   [x] v3.2 group-based material tags
-   [x] v3.2 separate meshes per group
-   [x] v3.2 group-specific bitmap export

### Texturing and materials

-   [x] Texture library
-   [x] User texture library
-   [x] Conformal texture mapping
-   [x] Seamless tiled textures
-   [x] TIFF texture sources
-   [x] Directional tiling
-   [x] Color maps
-   [x] Bump maps
-   [x] Specular highlights
-   [x] Self-illuminating textures
-   [x] Self-illuminating objects

### Lighting and environment

-   [x] Multiple lights
-   [x] Local lights
-   [x] Cast shadows
-   [x] Shadow opacity
-   [x] Shadow temperature
-   [x] Layered fog
-   [x] Sky gradients
-   [x] Star fields
-   [x] Scene presets

### Rendering and output

-   [x] Fully rendered workspace
-   [x] Antialiasing
-   [x] Graphical line mode
-   [x] Outline mode
-   [x] Polygon display mode
-   [x] Tessellation controls
-   [x] Brightness filter
-   [x] Contrast filter
-   [x] Saturation filter
-   [x] Hue filter
-   [x] TIFF output
-   [x] JPEG output
-   [x] BMP output
-   [x] AVI output (Windows)
-   [x] QuickTime output (Mac)
-   [x] Alpha output
-   [x] Depth/Z output
-   [x] Sequential frame output

### Animation

-   [x] Kinetic Morphing
-   [x] AutoBot animation strip
-   [x] Morph sequencing controls
-   [x] Morph movement controls
-   [x] Object-position changes
-   [x] Camera changes
-   [x] Lighting changes
-   [x] Background-color changes
-   [x] Animation preview

### Interface and workflow

-   [x] Multi-pane interface
-   [x] Library browser
-   [x] Drag-and-drop asset placement
-   [x] Selection and grouping panel
-   [x] Scene options panel
-   [x] Light options panel
-   [x] Texture options panel
-   [x] Bot options panel
-   [x] Edit and Animate workspaces
-   [x] Camera movement and rotation
-   [x] Camera zoom
-   [x] Lock Selection

------------------------------------------------------------------------

# 18. Documented limitations and cautions

A useful feature reference should also record the limitations reported
by people who used the software.

-   **Bot determinism:** A contemporary reviewer found that it could be
    difficult to reproduce exactly the same model twice through the
    organic Bot workflow. The review describes the output as not being
    under complete direct control.
-   **Learning curve:** The modeling and texturing controls were
    considered difficult to master without studying the documentation
    and experimenting.
-   **Animation compatibility:** Not all Bot types were available for
    Kinetic Morphing animation.
-   **Animation model:** The reviewed workflow was based on morphing
    between AutoBots, rather than a fully general-purpose animation
    timeline.
-   **Camera workflow:** The reviewer found camera and light adjustment
    cumbersome and wished for more convenient mouse navigation.
-   **Documentation gaps:** The contemporary review felt the supplied
    documentation was not sufficient to make modeling immediately
    straightforward.

These are observations from a contemporary review, not necessarily
universal limitations for every user or every v3.x build.

------------------------------------------------------------------------

# 19. Sources and further reading

The following sources were used to assemble this reference. Product
announcements are prioritized for official feature descriptions;
contemporary reviews and workflow documentation provide additional
practical detail.

1.  **CG Channel --- "GroBoto 3 gets real-time Boolean editing features"
    (February 25, 2011).**\
    The most useful v3.0 feature announcement, reproducing the product's
    key feature list and describing true-geometry Booleans, Flex Tools,
    automatic meshing, SeamNet, mesh density, and OBJ export.\
    https://www.cgchannel.com/2011/02/groboto-3-gets-real-time-boolean-editing-features/

2.  **Computer Graphics World --- "Braid Art Labs Introduces GroBoto 3D
    Art and Animation Software" (November 29, 2006).**\
    Original product announcement; documents Bots, Kinetic Morphing,
    relational editing, conformal texture mapping, lighting, rendering,
    alpha/depth output, and export.\
    https://www.cgw.com/Press-Center/News/2006/Braid-Art-Labs-Introduces-GroBoto-3D-Art-and-Ani.aspx

3.  **Computer Graphics World --- "Braid Art Labs Announces GroBoto 2.1"
    (June 19, 2007).**\
    Documents the inherited v2.1 features, including Strip mode, Bot
    presets, directional tiling, self-illumination, fog, sky gradients,
    star fields, morphing, image filters, and shadow controls.\
    https://www.cgw.com/Press-Center/News/2007/Braid-Art-Labs-Announces-GroBoto-2-1.aspx

4.  **3D Art Direct, Issue 8 --- "Groboto version 3 review" (May
    2011).**\
    Contemporary v3 review with interface layout, library categories,
    modeling workflow, Bot Options, texture controls, and practical
    Kinetic Morphing workflow.\
    https://www.scribd.com/document/894699920/Issue-08

5.  **GroBoto-to-modo Toolkit v104 guide.**\
    Third-party workflow guide documenting GroBoto v3.2 group-based
    material tags, separate meshes per group, group-specific maps,
    patch/seam data, and downstream mesh preparation.\
    https://www.scribd.com/document/139888411/GroBoto-Modo-Toolkit-v104

6.  **CG Channel --- "Braid Art Labs releases GroBoto 3.0 for Windows"
    (June 20, 2011).**\
    Confirms the Windows release of GroBoto 3.0.\
    https://www.cgchannel.com/2011/06/braid-art-labs-releases-groboto-3-0-for-windows/

7.  **TV Technology --- "GroBoto lets you create 3-D content on a
    standard desktop computer."**\
    Additional summary of rendering, Bot generation, texture mapping,
    fog, star fields, filters, line/outline rendering, and alpha/depth
    output.\
    https://www.tvtechnology.com/news/groboto-lets-you-create-3d-content-on-a-standard-desktop-computer

8.  **CGPress --- "GroBoto 3.0 now for Windows" (March 31, 2014).**\
    Additional confirmation of the Windows version and its
    primitive/Boolean-to-unified-mesh workflow.\
    https://cgpress.org/archives/groboto_3_0_now_for_windows.html

------------------------------------------------------------------------

## Closing note

GroBoto v3 is best understood as two closely related systems:

1.  **A generative art environment:** Bots, procedural growth, recursive
    structures, interactive editing, materials, lighting, environments,
    and Kinetic Morphing.
2.  **A procedural geometric modeling system:** True primitives, Boolean
    editing, Flex Tools, automatic mesh generation, SeamNet topology,
    density control, and structured OBJ export.

The distinctive value of GroBoto is the connection between those two
systems: the artist can explore and develop complex forms procedurally,
then turn the result into structured polygon geometry for use elsewhere.
