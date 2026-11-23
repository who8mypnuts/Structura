%!

% Beginning of spun knot wire frame prologue file.

gsave

-10 -10 10 10
44 centrebbox
adjbbox

/lw .1 def

/P {
  /y2 exch def
  /x2 exch def
  /y1 exch def
  /x1 exch def

  x2 x1 sub /xd exch def
  y2 y1 sub /yd exch def
  xd xd mul yd yd mul 
  add
  sqrt
  /length exch def

  length 0.0 ne 
  {
    xd length div /xd exch def
    yd length div /yd exch def

    newpath
    1 setgray
    lw setlinewidth
    x1 lw xd mul add y1 lw yd mul add moveto
    x1 length lw sub xd mul add y1 length lw sub yd mul add lineto
    stroke

    newpath
    0 setgray
    0 setlinewidth
    x1 y1 moveto
    x2 y2 lineto
    stroke
  } if

} def

% End of spun knot wire frame prologue file.


