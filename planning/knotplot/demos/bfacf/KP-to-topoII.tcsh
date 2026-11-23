#!/bin/tcsh -f


set n = 1

while ($n < 37)
  set knot = `knot-table -basic $n | tr "." "_"`

  switch ($n) 
  case 11:
  case 12:
  case 15:
  case 20:
  case 22:
  case 23:
  case 25:
  case 28:
  case 34:
    set both = false
    echo $knot
    breaksw
  default:
    set both = true
    breaksw
  endsw

  @ n++  
end

echo are mirrors of KnotPlot knots
