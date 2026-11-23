#!/bin/tcsh -f

set fout = init-boxes.kps
set panel = 18
set subpanel = 1

cp headbox $fout

#echo 'button 18 "Cavities" nop 4 265 102 10 4 '$subpanel >> $fout

set n = 1
set x = -2
set y = -1

foreach boxn (rect rings slab sphere tref walk curl cube blob tube xwing prism phage odd door)

  set box = $boxn".kps"

  echo $box


  switch ($boxn) 
  case door:
  case walk:
    set comm = "read bfacf/boxinit.kps;read bfacf/"$box
    breaksw
  default:
    set comm = "read bfacf/boxinit.kps;read bfacf/"$box";read bfacf/buttons.kps"
    breaksw
  endsw

  echo 'button '$panel' '$box:r' "'$comm'"' $x $y 0 0 0 $subpanel >> $fout
  set x = -1

  @ n++
end

echo 'button 18 "Min / max stick search" nop -2 -1 102 10 4 '$subpanel >> $fout

echo 'button pos 4' >> $fout
echo 'button 18 "README2"  "help popup bfacf/README-search.txt handoff" -1 -1 0 0 0 1' >> $fout


set x = -2

foreach boxn (1-slab 2-slab 3-slab) 

  set box = $boxn".kps"

  echo $box

  set comm = "read bfacf/boxinit.kps;read bfacf/"$box";read bfacf/buttons-search.kps"

  echo 'button '$panel' '$box:r' "'$comm'"' $x $y 0 0 0 $subpanel >> $fout
  set x = -1

  @ n++
end



echo 'button '$panel' PxQ_tube <bfacf/PxQ-tube.kps ' $x $y 0 0  0 $subpanel >> $fout


echo button Nbuttons 3 >> $fout
echo button hspace 4  >> $fout

foreach cpan (main disp dyna demoa demob bfacf0 bfacf1 bfacf2) 
  switch ($cpan)
  case bfacf0:
    set subpanel = 0
    set cpanel = bfacf
    breaksw
  case bfacf1:
    set subpanel = 1
    set cpanel = bfacf
    breaksw
  case bfacf2:
    set subpanel = 2
    set cpanel = bfacf
    breaksw
  default:
    set cpanel = $cpan
    set subpanel = 0
    breaksw
  endsw
  echo '%button '$cpanel'  "BFACF Basic" "panel set bfacf 0" 4 4 0 10 0 ' $subpanel >> $fout
  echo '%button '$cpanel'  "BFACF Fancy" "panel set bfacf 1" -1 -1 0 10 0 ' $subpanel >> $fout
  echo '%button '$cpanel'  "BFACF Demos" "panel set bfacf 2" -1 -1 0 10 0 ' $subpanel >> $fout

end

