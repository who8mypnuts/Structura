#!/bin/tcsh -f


set perko = PERKO_CORRECTED

if (-e $perko) then
  echo already perko corrected
else

  set n = 162
  set k = 163

  while ($k <= 166)
    echo mv "10."$k "10."$n
    mv "10."$k "10."$n

    @ k++
    @ n++
  end

  touch $perko

endif



