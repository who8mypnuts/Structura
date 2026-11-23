#! /bin/tcsh -f

touch cmode1 cmode11
/bin/rm cmode? cmode??
grep cmode nice-cmodes > dum1
set looping = true
set k = 0
echo " " > last-hdum

while ($looping == true)
  echo $k
  head -3 dum1 > hdum
  tail +4 dum1 > tdum
  mv tdum dum1

  set d = `diff hdum last-hdum | wc -l`
  set d = $d[1]

  if ($d != 0) then
    echo $k $d
    cp hdum cmode$k
    cp hdum last-hdum
    @ k++
  endif

  set n = `wc -l dum1`
  set n = $n[1]
  if ($n < 3) then
    set looping = false
  endif

end


