#!/bin/tcsh -f


set n = 251

set n = 2
#while ($n < 251)
while ($n < 343)
  set knot = `knot-table -basic $n`
  set nseg = `wc $knot`
  set nseg = $nseg[1]
  echo $n $knot $nseg
  @ n++
end

  
