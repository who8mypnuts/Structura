#!/bin/tcsh  -f

set fout = "fix-cats.kps"

echo "allo 9999" > $fout

foreach f (c[3-8]/*.k d[3-8]/*.k) 
  echo load $f >> $fout
  echo save "new/"$f " LOCS" >> $fout
end

