#version 2
// Primitives — every v2 shape: cylinder, cone, torus, ellipsoid and tube, beside the classic box and sphere.
// Bracket arguments set a shape's proportions: cone[0.4] has a top 0.4 as wide; torus[0.3] a thicker ring.

material clay { preset clay }
light key  { type rect  position [-4 7 6]  target [0 0 0]  size [4 4]  power 900  color #fff5ea }
light rim  { type rect  position [3 4 -6]  target [0 0 0]  size [2 2]  power 300 }
environment { type gradient  top #d9dee6  bottom #5b5e63 }
camera { position [0 4.5 12]  target [0 0.3 -0.8]  lens 28mm }
render { integrator path  samples 192  ground plane  ground_color #8a8f96 }

{ color #e07a5f } shelf

rule shelf {
  { x -6 ry 90 rz 90 s 1.2 } cylinder::clay
  { x -3.6 rz 90 s 1.2 color #f2cc8f } cone::clay
  { x -1.2 rz 90 s 1.2 color #81b29a } cone[0.4]::clay
  { x 1.2 rx 90 s 1.4 color #3d405b } torus[0.3]::clay
  { x 3.6 s 1.4 0.8 1 color #f4a261 } ellipsoid::clay
  { x 5.4 y 0.6 s 1.4 color #2a9d8f } tube[0.25]
  { z -3 x -1.5 color #bbbbbb } box::clay
  { z -3 x 1.5 color #bbbbbb } sphere::clay
}
