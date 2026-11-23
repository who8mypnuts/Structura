#!/bin/tcsh -f

set fout = ../demos/CelticGridExamples.kps
echo -n "%% Generated  " > $fout
date >> $fout
echo  " " >> $fout

set hspace = 4

echo button Nbuttons 5 >> $fout
echo button hspace $hspace >> $fout
echo button pos 0 >> $fout

set x = $hspace
set y = 75

echo " " >> $fout

echo button Sketch '"Example grids"' nop $hspace $y 40 10 4  1 >> $fout
@ y -= 10

echo " " >> $fout




foreach f (josephine.k gbain*.k ibain*.k am-p*.k ??ck*.k celtic*.k)
  set bname = $f:r
  echo button Sketch $bname '"echo;echo;load '$f';echo (click on diagram button to see knot);echo"' $x $y 0 8  0 1 >> $fout
  set x = -1
  set y = -1
  echo $f
end

set weird = 1

foreach f (weird_celtic*.k)
  set bname = "weird"$weird
  echo button Sketch $bname '"echo;echo;load '$f';echo (click on diagram button to see knot);echo"' $x $y 0 8  0 1 >> $fout
  set x = -1
  set y = -1
  echo $f
  @ weird++
end

