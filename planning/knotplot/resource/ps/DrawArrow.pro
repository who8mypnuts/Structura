%% Begin DrawArrow.pro 

%% Rob Scharein
%% November 19, 1996

% The following three parameters may be changed to produce different effects.
% In particular, make ArrowScale negative to get the arrow to point backwards.
% ArrowRot may be used to to rotate the arrow so that it aligns correctly.


/ArrowScale 1 def  % Make negative to invert 
/ArrowWidth 1 def  
/ArrowRot   0 def  % Rotation in degrees (0 to 360)

/DrawArrow {
  gsave
  0 setlinewidth
  0 setgray
  pop
  toPS
  /yb exch def
  /xb exch def
  pop
  toPS 
  /ya exch def
  /xa exch def
  
  /dx xa xb sub def
  /dy ya yb sub def
  /norm dx dup mul dy dup mul add sqrt 88 ArrowScale mul div def
  /dx dx norm div def
  /dy dy norm div def
  /rat 3 ArrowWidth mul def
  /ex dy -1 mul rat div def
  /ey dx rat div def
 
  gsave
  xb yb translate
  ArrowRot rotate
  newpath
  0 0  moveto 
  ex ey  lineto
  dx dy  lineto
  0 ex sub 0 ey sub lineto
  closepath
  fill
  grestore

} def

%% End DrawArrow.pro 

