#version 2
// Sunset City — a low warm sun over a random city block (the 'Sunset' lighting rig, Cinematic look).

material glass_front { preset glass  thin_walled true }
material concrete    { preset clay  base #b9b2a7 }

light sun { type sun  direction [0.75 -0.18 -0.62]  intensity 2.6  angle 1.2  color #ffb27a }
environment { type sunsky  sun sun  turbidity 4 }
camera { position [-22 9 26]  target [0 2 0]  lens 35mm }
render { integrator path  samples 256  ground plane  ground_color #3b3a38  look cinematic }

set maxdepth 400
set seed 7
{ x -12 z -12 } blocks

rule blocks { 9 * { x 3 } 9 * { z 3 } plot }

rule plot { { s 2.4 (rand(1, 9)) 2.4 y 0.5 } tower }
rule plot w 0.35 { { s 2.4 0.4 2.4 color #4d6b3c } box::concrete }

rule tower { box::concrete }
rule tower w 0.5 { { s 0.98 1 0.98 } box::glass_front  { s 1.02 0.02 1.02 y 0.5 } box::concrete }
