#!/bin/tcsh -f

set fout = init-load.kps
set panel = 18

cp headload $fout

set n = 1
set x = -2
set y = -1

set w2KP = "Writhe-to-KnotPlot.txt"
cp w2KP-header.txt $w2KP

while ($n < 37)
  set knot = `knot-table -basic $n | tr "." "_"`
  echo $knot

  echo -n $knot" " >> $w2KP

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
    echo $knot is TopoII only
    echo flipped >> $w2KP
    breaksw
  default:
    set both = true
    echo same >> $w2KP
    breaksw
  endsw
  
  

#  set file = "initial/"$knot"_coords.txt"
  set file = $knot
  if ($both == true) then
    set comm = "read bfacf/basicinit.kps;bfacf load mscl/$file;panel set bfacf 0;echo knot follows both TopoII and KnotPlot conventions"
  else
    set comm = "read bfacf/basicinit.kps;bfacf load mscl/$file;panel set bfacf 0;echo knot follows TopoII convention only"
  endif
  echo 'button '$panel' '$knot' "'$comm'"' $x $y 0 0 0 3 >> $fout
  set x = -1


  set file = "initial/"$knot"s_coords.txt"
  set file2 = $knot'STAR'

  if (-e $file) then
    if ($both == true) then
      set comm = "read bfacf/basicinit.kps;load mscl/$file2;bfacf load;panel set bfacf 0;echo knot follows both TopoII and KnotPlot conventions"
    else
      set comm = "read bfacf/basicinit.kps;load mscl/$file2;bfacf load;panel set bfacf 0;echo knot follows TopoII convention only"
    endif
    echo 'button '$panel' '$knot'STAR "'$comm'"' $x $y 0 0 0 3 >> $fout
    set x = -1
  endif



  @ n++
end

set x = -2
set y = -1



foreach knot (6c_1 6c_1s 6c_2 7c_1 7c_1s 8c_1 8c_1s 8c_2 8c_2s 8c_3 8c_3s 8c_4 8c_4s 8c_5)

  echo $knot

  set file = $knot
  set comm = "read bfacf/basicinit.kps;bfacf load $file;panel set bfacf 0;echo knot follows both TopoII and KnotPlot conventions"
  echo 'button '$panel' '$knot' "'$comm'"' $x $y 0 0 0 3 >> $fout
  set x = -1

end

echo 'button 18 "KnotPlot catalog" nop 4 -2 102 10 4 3' >> $fout
echo 'button bfacf "1 comp" "ccmode=2;knot numb \ri[1/250] mscl;bfacf load;panel set bfacf 0" -2 -1 -2 0 0 3' >> $fout
echo 'button bfacf "2 comp" "ccmode=2;knot numb \ri[251/342] mscl;bfacf load;panel set bfacf 0" -1 -1 -2 0 0 3' >> $fout
echo 'button bfacf "3 comp" "ccmode=2;knot numb \ri[343/378] mscl;bfacf load;panel set bfacf 0" -1 -1 -2 0 0 3' >> $fout
echo 'button bfacf "4 comp" "ccmode=2;knot numb \ri[379/383] mscl;bfacf load;panel set bfacf 0" -1 -1 -2 0 0 3' >> $fout

echo 'button 18 " " nop 4 -2 102 10 4 3' >> $fout
echo 'button pos 3' >> $fout
echo 'button 18 cancel "panel set bfacf 0" -1 -1 -2 0 0 3' >> $fout


echo 'button 18 "*** NEW: click on the `help'"'"' button for important information" nop 4 -2 102 10 4 3' >> $fout

sed 's|STAR|*|g' $fout > dum
mv dum $fout

