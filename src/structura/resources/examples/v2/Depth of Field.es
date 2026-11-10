#version 2
// Depth of Field — a photographic lens: 85 mm at f/1.8, focused on the middle of the row.
// 'scale' says how many world units make a metre (40: a tabletop miniature), so the f-stop blurs like a real
// lens would at that size.
// Try the Camera panel's lens editor, or click a column with 'Focus on selection'.

material brass { preset gold  roughness 0.25 }
light sun { type sun  direction [-0.6 -0.7 -0.4]  intensity 3  angle 1.5 }
environment { type sunsky  sun sun }
camera {
  position [9 3.5 30]  target [2 2 -4]
  lens 85mm  fstop 1.8  focus auto  scale 40  blades 7
}
render { integrator path  samples 384  ground plane  ground_color #6f6a64  denoise auto }

set maxdepth 40
{ z 8 } columns

rule columns { 9 * { z -3 x 0.5 } column }

rule column {
  { y 1.5 s 0.6 3 0.6 } cylinder::brass
  { y 3.2 s 0.9 } sphere::brass
}
