#version 2
// Studio Product — a lighting rig written by the Lights panel ('Lighting Rig ▸ Studio softbox').
// Rig lights are named rig_…; applying another rig replaces them. Edit any number: the script is the truth.

material ceramic { preset ceramic }
material chrome  { preset chrome }

environment {
  type color
  color #1b1c1f
}
// lighting rig: Studio softbox (Structura; lights named rig_… are replaced when another rig is applied)
light rig_key {
  type rect
  position [-9.6 9.6 12]
  target [0 0 0]
  size [9.6 9.6]
  power 2700
  color #fff4e8
}
light rig_fill {
  type rect
  position [14.4 2.4 9.6]
  target [0 0 0]
  size [13.2 13.2]
  power 680
  color #e8f0ff
}
light rig_rim {
  type rect
  position [4.8 10.8 -13.2]
  target [0 0 0]
  size [6 6]
  power 1600
}
camera { position [0 6 22]  target [0 0 0]  lens 70mm }
render { integrator path  samples 256  ground plane  ground_color #2a2b2f  look studio }

set maxdepth 12
{ color #f1efe9 } vase

rule vase {
  12 * { ry 30 } petal
  { s 2.2 0.3 2.2 y -8 } cylinder::chrome
}

rule petal {
  { z 1.6 rx -20 s 0.5 4 0.3 } ellipsoid::ceramic
}
