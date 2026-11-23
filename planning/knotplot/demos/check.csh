#! /bin/tcsh -f

echo " " > dum

foreach f (*.kps) 
  echo $f
  echo $f >> dum
  diff $f ../$f >> dum
end

