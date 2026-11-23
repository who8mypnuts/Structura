#!/bin/tcsh -f

set x = -2
set fout = buttons.kps
echo " " > $fout


foreach f ([3-7]*1.k 8_?-*1.k 8_??-*1.k 9_?-*1.k 9_??-*1.k 10_?-*1.k 10_??-*1.k 10_???-*1.k)
  set knot = `echo $f | sed 's|-1slab-1.k||'`
  set kpsf = $knot".kps"
  set knot1 = $knot"-1slab-1.k"
  set knot2 = $knot"-1slab-2.k"

  set nb1 = `kpfsnoop -b $knot1`
  set nb2 = `kpfsnoop -b $knot2`
 
  echo $knot $kpsf $knot1 $nb1 $knot2 $nb2

  set knotm = $knot"-1slab.k"
  echo cp $knot1 $knotm
  cp $knot1 $knotm

  echo 'button bfacf '$knot' <bfacf/ergod/'$knot'.kps ' $x -1 0 0 0 2 >> $fout
  set x = -1

  sed 's|KNOT|'$knot'|g' template.kps > $kpsf

end

