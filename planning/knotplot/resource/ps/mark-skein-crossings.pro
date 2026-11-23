
/FindMid {
  Under cos Over cos mul
  Under sin Over sin mul
  add                      % dot product

  0 gt
  {/Under 180 Under add def}
  if

  Under sin Over sin add
  Under cos Over cos add
  atan

  /MidA exch def
  

} def

/crossing {
  1 eq
  {
    /xing {Plus} def
  }
  { 
    /xing {Minus} def
  }
  ifelse

  /Over  exch def
  /Under exch def
  FindMid


  gsave
  translate

  %0 1 0 setrgbcolor

  MidA cos xxx mul MidA sin xxx mul
  xing

  /MidA MidA 180 add def
  MidA cos xxx mul MidA sin xxx mul
  xing


  %DrawLines

  grestore

} def


/DrawLines {
  gsave

  .5 0 .5 setrgbcolor
  MidA rotate
  .3 ScaleFactor mul  setlinewidth
  0 0 moveto
  -10 ScaleFactor mul 0 lineto
  stroke

  grestore

  gsave

  1 0 0 setrgbcolor
  Under rotate
  .3 ScaleFactor mul  setlinewidth
  0 0 moveto
  -10 ScaleFactor mul 0 lineto
  stroke

  grestore

  gsave

  0 0 1 setrgbcolor
  Over rotate
  .3 ScaleFactor mul  setlinewidth
  0 0 moveto
  -10 ScaleFactor mul 0 lineto
  stroke

  grestore

} def

/xxx ScaleFactor 4.3 mul def
/mxx xxx -1 mul def
/sss xxx .25 mul def
/mss sss -1 mul def

/Plus {
  gsave 
  translate
  0 0 
  Minus
  90 rotate
  0 0 
  Minus
  grestore
} def

/Minus {
  gsave
  .4 ScaleFactor mul setlinewidth
  newpath
  translate
  mss 0 moveto
  sss 0 lineto
  stroke
  grestore
} def

