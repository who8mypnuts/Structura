#! /bin/tcsh -f

foreach f (*.kps basic-demos)
  cat $f | tr -d '\r' > dum.r
  set n = `diff dum.r $f | wc -l`
  if ($n > 0) then
    echo $f"  "$n
    set k = `cat dum.r | wc -l`
    set p = `cat $f | wc -l`
    echo $k $p
    if ($k == $p) then
      mv dum.r $f
    else 
      echo "Super bad data"
      exit
    endif 
  endif
end
