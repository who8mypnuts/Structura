#version 2
// Glass Garden — glass, tinted glass, metal and plastic under a clear sky (EisenScript v2).
// Glass needs the path integrator; 'attenuation' tints the glass by its thickness (Beer–Lambert).

material clear  { preset glass  roughness 0 }
material amber  { preset glass  attenuation_color #ff9a2e  attenuation_distance 2.5 }
material frosted { preset glass  transmission_roughness 0.35 }
material brushed { preset metal  roughness 0.3  anisotropy 0.7 }
material glossy { preset plastic  roughness 0.08 }

light sun { type sun  direction [-0.5 -0.9 -0.35]  intensity 3  angle 1  color #fff3e0 }
environment { type sunsky  sun sun  turbidity 2.5 }
camera { position [6 4.5 11]  target [0 0.9 0]  lens 40mm  fstop 4  focus auto }
render { integrator path  samples 256  ground plane  ground_color #c9c4bc  look subtle }

set maxdepth 60
{ color #e9e4da } garden

rule garden {
  { x -2.4 y 1 s 2 } sphere::clear
  { x 0 y 1 s 2 } sphere::amber
  { x 2.4 y 1 s 2 } sphere::frosted
  { z -2.6 y 0.6 s 1.2 } row
  { z 2.4 y 0.25 s 5 0.5 0.5 color #d0463c } box::glossy
}

rule row { { x -3 } bars }
rule bars { 6 * { x 1.1 ry 15 } box::brushed }
