#! /bin/tcsh -f
 
echo " " > dum
 
set Ndiff = 0
set Nmissing = 0
 
foreach f (*.cpp *.c *.h *.kps *.y)
  set other = ../$f

  if (-e $other) then
    echo $f $other
    echo $f $other >> dum
    diff $f $other > dum.diff
   
    set n = `wc -l dum.diff`
    if ($n[1] > 0) then
      cat dum.diff >> dum
      @ Ndiff++
    endif
  else
    echo 
    echo "**** File "$other" is missing. ****"
    echo 
    @ Nmissing++
  endif
end
 
echo " "
echo $Ndiff files differ.
echo $Nmissing files missing.

touch dum.diff
/bin/rm dum.diff
 
