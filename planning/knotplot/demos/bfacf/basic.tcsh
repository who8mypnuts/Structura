#!/bin/tcsh -f

set fout = init-basic.kps
set panel = 18

cp headbasic $fout


set x = -1
set y = -1


echo 'button Nbuttons 4' >> $fout

foreach f (link open obstacles)
  echo 'button '$panel' '$f' <bfacf/'$f'.kps ' $x $y 0 0 >> $fout
  set x = -1
end


echo 'button '$panel' "centre on" "bfacf centre on" ' $x $y 0 0 >> $fout
set x = -1
echo 'button '$panel' "centre off" "bfacf centre off" ' $x $y 0 0 >> $fout
echo 'button '$panel' "tclasp" "<bfacf/tclasp.kps" ' $x $y 0 0 >> $fout
echo 'button '$panel' "tclasp box" "<bfacf/tclasp-box.kps" ' $x $y 0 0 >> $fout
echo 'button '$panel' "parsites" "<bfacf/bclasp.kps" ' $x $y 0 0 >> $fout
echo 'button '$panel' "recombo" "<bfacf/recombo.kps" ' $x $y 0 0 >> $fout
echo 'button '$panel' "clasp" "<bfacf/acclasp.kps" ' $x $y 0 0 >> $fout
echo 'button '$panel' "UofS clasp" "<bfacf/UofS-clasp.kps" ' $x $y 0 0 >> $fout


echo 'button '$panel' "freeze 0" "bfacf freeze 0" ' -2 $y 0 0 >> $fout
echo 'button '$panel' "thaw 0" "bfacf thaw 0" ' $x $y 0 0 >> $fout
echo 'button '$panel' "freeze 1" "bfacf freeze 1" ' $x $y 0 0 >> $fout
echo 'button '$panel' "thaw 1" "bfacf thaw 1" ' $x $y 0 0 >> $fout

echo 'button '$panel' "embed" "<bfacf/embed.kps" ' $x $y 0 0 >> $fout
echo 'button '$panel' "bfacf load" "<bfacf/load.kps" ' $x $y 0 0 >> $fout
echo 'button '$panel' "standard" "<bfacf/standard.kps" ' $x $y 0 0 >> $fout
echo 'button '$panel' "minstep" "<bfacf/minstep.kps" ' $x $y 0 0 >> $fout


exit

echo 'button '$panel' "Run with step size:" nop 4 124 102 10 4' >> $fout
set x = -2
echo 'button Nbuttons 4' >> $fout
echo 'button blank _' >> $fout

foreach f (1 10 100 1000 10000 100000 1000000)
  echo 'button '$panel' '$f' "bfacf setstep '$f';<bfacf/idle-basic.kps"' $x $y 0 0 >> $fout
  set x = -1
end


echo 'button '$panel' STOP idle' $x $y 0 0 >> $fout

