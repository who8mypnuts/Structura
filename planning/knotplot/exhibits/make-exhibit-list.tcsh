#!/bin/tcsh -f

set fout = ExhibitList.kps
set tout = ExhibitTest.kps

echo -n "%% Auto-generated on " > $fout
date >> $fout
echo >> $fout

cp $fout $tout

# test panel is DemoA/10

echo 'button DemoA "NeverEnding exhibitions (ESC to exit)" dum -2 -1 102 10 4' >> $fout
echo 'button DemoA "Test exhibitions" dum 4 270 102 10 4 10' >> $tout
echo 'button Nbuttons 4' >> $tout
echo 'button hspace 4' >> $tout
echo 'button pos 1' >> $tout

touch list.tmp
/bin/rm list.tmp

foreach dir (*)
  if (-d $dir) then
    if (-e $dir/info.txt) then 
      set name = `head -1 $dir/info.txt | tr " " "_" | tr -d "\r"`
      set priority = `tail +2 $dir/info.txt | tr -d "\r"`
      echo Adding exhibit $name in directory $dir with priority $priority 
      echo $priority $dir.$name >> list.tmp
    endif
  endif
end

set xpos = -2

foreach f (`sort -n list.tmp | awk '{print $2, $3}'`)
  set dir = $f:r
  set name = $f:e
  echo 'button DemoA "'$name'" "read ExhibitSplash.kps;func c 12 panel off:path KPHOME exhibits/'$dir':<start-demo.kps" '$xpos' -1 0 0' >> $fout
  echo 'button DemoA "'$name'" "path KPHOME exhibits/'$dir';<TestDemos.kps" '$xpos' -1 0 10 0 0' >> $tout
  set xpos = -1
end

/bin/rm *.tmp
