#!/bin/csh -f

touch dum dum1
/bin/rm dum dum1

foreach f (*)
  echo $f

  grep ";" $f | grep fun > dum1
  grep , $f >> dum1

  set n = `wc -c dum1`
  
  switch ($n[1])
  case 0:
    breaksw
  default:
    echo " " >> dum
    echo " " >> dum
    echo " " >> dum
    echo $f >> dum
    cat dum1 >> dum
    breaksw
  endsw
end

