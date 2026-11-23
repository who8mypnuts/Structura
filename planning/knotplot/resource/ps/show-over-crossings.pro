/beadR 30 def
0.8 beadR mul /beadr exch def

/crossing {               % Draw a bead at (xloc, yloc)

  pop pop

  /tang exch def
  tang cos 10 mul /xinc exch def
  tang sin 10 mul /yinc exch def

  0 setlinewidth
  0 setgray
  /yloc exch def
  /xloc exch def

  newpath
  xloc yloc moveto
  xloc yloc beadR 0 360 arc
  fill

  newpath
  1 setgray 
  xloc yloc moveto
  xloc yloc beadr 0 360 arc
  fill

  newpath
  0 setgray
  xloc yloc moveto
  2 setlinewidth
  xinc yinc rmoveto
  -2 xinc mul -2 yinc mul rlineto
  stroke

} def

