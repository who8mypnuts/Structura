%!
%  mark-clusters.pro
%  

/ClusterMark {     % Draw a filled circle at (xloc, yloc)
  gsave

  toPS
  translate
  0 setlinewidth
  0 setgray

  newpath
  0 0 moveto
  0 0 ClusterRadius psScale mul 0 360 arc
  fill

  grestore
} def

% end of mark-clusters.pro

