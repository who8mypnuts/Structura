#!/bin/tcsh -f

set tmpfile = sfdksjojsd.tmp

foreach f (*.kps)
  echo $f 
  sed -f fix.sedf $f > $tmpfile
  mv $tmpfile $f
end
