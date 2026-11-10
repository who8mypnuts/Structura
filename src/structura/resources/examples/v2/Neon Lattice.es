#version 2
// Neon Lattice — glowing tubes in the dark with bloom (EisenScript v2).
// Emission makes a material a light source; the Neon look adds bloom around everything that glows.

material neon_pink { base #ff2bd6  emission #ff2bd6 6 }
material neon_cyan { base #18e0ff  emission #18e0ff 6 }
material dark      { preset metal  base #1a1c22  roughness 0.25 }

environment { type color  color #040508 }
camera { position [0 9 15]  target [0 0 0]  fov 38 }
render { integrator path  samples 256  look neon  bloom 0.35  vignette 0.3 }

set maxdepth 200
{ s 0.9 } lattice

rule lattice { { x -4 z -4 } cells }
rule cells { 5 * { x 2 } 5 * { z 2 } cell }

rule cell {
  { s 0.12 1.6 0.12 } box::dark
  { y 0.85 s 1.2 } torus[0.08]::neon_pink
  { y -0.85 s 1.2 ry 45 } torus[0.08]::neon_cyan
}

rule cell w 0.4 {
  { s 0.12 1.6 0.12 } box::dark
  { y 0.85 s 0.5 } sphere::neon_cyan
}
