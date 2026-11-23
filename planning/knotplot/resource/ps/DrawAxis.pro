
0 setgray


/DrawAxis {
  lineto
  stroke
} def

/Circsize 20 def
/circsize Circsize 0.75 mul def

/DrawAxes {
  6 setlinewidth
  1 setlinecap 
  toPS
  /y2 exch def
  /y1 exch def
  toPS
  /x2 exch def
  /x1 exch def
  toPS
  /o2 exch def
  /o1 exch def

  o1 o2 moveto
  x1 x2 DrawAxis

  o1 o2 moveto
  y1 y2 DrawAxis

  gsave

  0 setlinewidth

  newpath
  o1 o2 moveto
  o1 o2 Circsize 0 360 arc
  fill

  0 lt 
  {
    1 setgray
    o1 o2 moveto
    o1 o2 circsize 0 360 arc
    fill
  } if
    
  grestore

} def

/fontsize 88 def
/Helvetica findfont fontsize scalefont setfont

/drawx {
  (x) stringwidth
  pop  -.5 mul fontsize -.25 mul
  moveto
  (x) show  
} def

/drawy {
  (y) stringwidth
  pop  -.5 mul fontsize -.17 mul
  moveto
  (y) show  

} def

/drawz {
  (z) stringwidth
  pop  -.5 mul fontsize -.25 mul
  moveto
  (z) show  

} def







