#!/bin/tcsh -f

foreach f (*.kps)

  echo $f
  sed -f fix.sedf $f > dum
  mv dum $f

end
