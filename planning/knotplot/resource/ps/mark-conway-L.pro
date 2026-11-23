%!
%  mark-conway-L.pro
%  

/beadR 30 def
/gr 5 sqrt 1 add 2 div def

/cww 1 gr div def

% xpos ypos over-xing-angle under-xing-angle crossing-type crossing

/crossing {   
  gsave

  /xingtype exch def
  pop 

  3 1 roll

  0 setlinewidth
  0 setgray

  newpath

  translate

  Acons mul Bcons add
  45 sub rotate     % Angle of overcrossing minus 45

  beadR dup scale
  0 0  1 0 360 arc  % Draw a filled unit circle
  fill

  newpath
  1 setgray 
  0 0 moveto
  0 0 0.8 0 360 arc % Hollow out the interior
  fill

  .3 dup scale      % Size of L relative to unit circle

  ConwayL
  
  grestore

} def

/Ltype 0 def
/Acons 1 def
/Bcons 0 def

/ConwayL {
  gsave

  10 Ltype eq {90 rotate -1 1 scale} if
  /Ltype 0 def

  -1 xingtype eq {-1 1 scale} if

  newpath
  0 setgray
  0 0  moveto
  0 setlinewidth
  
  -1 0 rmoveto
  0 gr rmoveto
  0 gr -2 mul rlineto
  2 0 rlineto
  0 cww rlineto
  -2 cww add 0 rlineto
  0 2 gr mul cww sub rlineto

  closepath
  fill

  grestore
} def

