#!/bin/tcsh -f

set fout = init-panels.kps
set panel = 18

cp header $fout

set n = 1
set x = -2
set y = -1

while ($n < 37)
  set knot = `knot-table -basic $n | tr "." "_"`
  echo $knot

  set file = "initial/"$knot"_coords.txt"
  set comm = "bfacf init;bfacf load $file"
  echo 'button '$panel' '$knot' "'$comm'"' $x $y 0 0 >> $fout
  set x = -1

  set file = "initial/"$knot"s_coords.txt"
  if (-e $file) then
    set comm = "bfacf init;bfacf load $file"
    echo 'button '$panel' '$knot'* "'$comm'"' $x $y 0 0 >> $fout
    set x = -1
  endif



  @ n++
end

#echo 'button $panel "Oddities" nop 4 -2 102 10 4' >> $fout

foreach f (link open obstacle1 obstacle2)
  echo 'button '$panel' '$f' <'$f'.kps ' $x $y -2 0 >> $fout
  set x = -1
end

echo 'button '$panel' "Run with step size:" nop 4 -2 102 10 4' >> $fout
set x = -2
echo 'button Nbuttons 4' >> $fout

foreach f (1 10 100 1000 10000 100000 1000000)
  echo 'button '$panel' '$f' "par5='$f';<idle.kps"' $x $y 0 0 >> $fout
  set x = -1
end


echo 'button '$panel' STOP idle' $x $y 0 0 >> $fout


echo 'button '$panel' freeze_0 "bfacf freeze 0" ' $x $y 0 0 >> $fout
echo 'button '$panel' thaw_0 "bfacf thaw 0" ' $x $y 0 0 >> $fout
echo 'button '$panel' freeze_1 "bfacf freeze 1" ' $x $y 0 0 >> $fout
echo 'button '$panel' thaw_1 "bfacf thaw 1" ' $x $y 0 0 >> $fout

echo 'button '$panel' centre_on "bfacf centre on" ' $x $y 0 0 >> $fout
echo 'button '$panel' centre_off "bfacf centre off" ' $x $y 0 0 >> $fout
