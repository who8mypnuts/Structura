#version 2
// Medusarium M1 — a moon jelly (Aurelia-like medusa) in EisenScript v2.
// Anatomy: a flattened bell (ellipsoid), a scalloped margin (torus + lobe bumps),
// a ring of thin marginal tentacles, a few thick wavy oral arms, and a dense fringe
// of short hairs. Every shape is a v2 primitive; every variation comes from the
// #params below and the build seed — there is no creature-specific code.
//
// Try it: open this script, move the sliders in the Parameters panel, and hit
// Randomize (a new seed redraws the tentacle chains).

#param radius float = 1.4 range 0.6..3.0 "Radius"
#param tentacles int = 10 range 1..32 "Tentacles"
#param segments int = 8 range 2..30 "Tentacle length"
#param bend float = 14 range 0..40 "Tentacle bend"
#param taper float = 0.965 range 0.90..0.995 "Taper"
#param oral int = 6 range 1..16 "Oral arms"
#param lobes int = 8 range 0..24 "Bell lobes"
#param fringe int = 48 range 0..160 "Fringe hairs"
#param fringe_depth int = 5 range 2..16 "Fringe length"
#param bell_color color = #d988b0
#param rim_color color = #e8c2d4
#param tent_color color = #9db8e8
#param strand_color color = #b8c8f0

// Soft studio: warm fill, cool rim, paper background — the Cindermedusae look.
material dome  { preset plastic roughness 0.3  transmission 0.6 }
material strand { preset plastic roughness 0.45 }
material hair   { preset plastic roughness 0.5 }

light fill { type sphere  position [-3 -1 0] radius 4 power 400 color #fff2e0 }
light rim  { type point   position [2 3 2] power 300 color #bcd8ff }
environment { type color color #f5eddc }
camera { position [0 1.1 7.5] target [0 0.4 0] lens 40mm }
render { integrator path samples 128 }

set maxdepth 60
medusa

rule medusa {
  { s (radius) } creature
}

rule creature {
  // Bell: flattened dome, then the scalloped margin.
  { color bell_color s 1.5 0.85 1.5 } ellipsoid::dome
  { color rim_color y -0.22 s 0.8 0.25 0.8 } torus[0.45]::dome
  // Lobe bumps around the rim (the bell's scallops); 0 hides them.
  (lobes) * { ry (360/max(lobes,1)) x 0.62 y -0.28 } lobe
  // Marginal tentacles: a thin ring of tapered, gently bending chains.
  (tentacles) * { ry (360/max(tentacles,1)) x 0.6 y -0.12 rx 180 } tentacle
  // Oral arms: fewer, thicker, wavier, closer to the mouth.
  (oral) * { ry (360/max(oral,1)) x 0.28 y -0.05 rx 180 } oralarm
  // Fringe: dense short hairs just under the margin.
  (fringe) * { ry (360/max(fringe,1)) x 0.72 y -0.15 rx -55 } fringestr
}

rule lobe {
  { color bell_color s 0.3 } sphere::dome
}

// A tentacle is a chain of segments, each shorter and slightly rotated.
// Three weighted variants (chosen per segment from the seed stream) give the
// chain an organic, non-uniform sway; 'tip' retires the chain.
rule tentacle md (segments) > tip w 3 {
  { color tent_color s 0.075 1 0.075 } box::strand
  { y 0.94 s (taper) rz (bend) } tentacle
}
rule tentacle md (segments) > tip w 1 {
  { color tent_color s 0.075 1 0.075 } box::strand
  { y 0.94 s (taper) rz (-(bend * 0.6)) } tentacle
}
rule tentacle md (segments) > tip w 1 {
  { color tent_color s 0.075 1 0.075 } box::strand
  { y 0.94 s (taper) ry (14) rz (bend * 0.4) } tentacle
}
rule tip {
  { color tent_color s 0.45 } dot::strand
}

// Oral arms: the same chain idea, thicker and with a stronger wave.
rule oralarm md 14 > oraltip w 2 {
  { color tent_color s 0.12 1 0.12 } tube[0.4]::dome
  { y 0.9 s 0.97 rz (bend * 1.6) } oralarm
}
rule oralarm md 14 > oraltip w 1 {
  { color tent_color s 0.12 1 0.12 } tube[0.4]::dome
  { y 0.9 s 0.97 rz (-(bend * 1.2)) } oralarm
}
rule oraltip {
  { color tent_color s 0.7 } dot::dome
}

// Fringe hairs: short dense strands under the margin.
rule fringestr md (fringe_depth) > fringetip w 2 {
  { color strand_color s 0.028 1 0.028 } box::hair
  { y 0.9 s 0.88 rz (bend * 1.5) } fringestr
}
rule fringestr md (fringe_depth) > fringetip w 1 {
  { color strand_color s 0.028 1 0.028 } box::hair
  { y 0.9 s 0.88 rz (-(bend * 1.5)) } fringestr
}
rule fringetip {
  { color strand_color s 0.3 } dot::hair
}
