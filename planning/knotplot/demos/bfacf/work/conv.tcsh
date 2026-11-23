#!/bin/tcsh -f

foreach f (*config*kps)
  set g = `echo $f | tr -d "a-z" | tr -d ".-"`
  if ($g > 20) then
    @ g -= 20
  endif
  echo $f $g

  echo "txt clobber on"  >> $f
  echo "txt font 2"  >> $f
  echo "txt fill off"  >> $f
  echo "txt cent"   >> $f
  echo 'txt c -44 "configuration '$g'"'  >> $f
end
