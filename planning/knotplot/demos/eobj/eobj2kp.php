#!/usr/bin/php
<?php

function createEdge ($n1, $n2) {
  global $adjacent;
  $adjacent [min ($n1, $n2)][max ($n1, $n2)] = true;
}

$fp = fopen ($argv [1], "r");

// skip first line
fgets ($fp);
$nnode = rtrim (fgets ($fp));

print "% $nnode nodes in graph\n";
for ($i = 0; $i < $nnode; $i++)
  $node [$i] = rtrim (fgets ($fp));

while ($stuff = rtrim (fgets ($fp))) {
  $thing = explode (" ", $stuff);
  if ($thing [0] == "f") {   // is a face
    array_shift ($thing);    // get rid of first element ("f") in array
    for ($i = 0; $i < count ($thing); $i++) {
      createEdge ($thing [$i], $thing [($i + 1) % count ($thing)]);
    }
  }
}


fclose ($fp);

print "delete all\nnew=f\n\n";

$comp = 0;
foreach ($adjacent as $n1=>$nodes) {
  foreach ($nodes as $n2=>$ignore) {
    printf ("%% component %d from node %d to node %d\nline %s %s\n\n",
	    $comp, $n1, $n2, $node [$n1], $node [$n2]);
    $end_at [$n1][] = "f$comp";
    $end_at [$n2][] = "l$comp";
    $comp++;
  }
}

print "\n\n";

for ($i = 0; $i < count ($node); $i++) {
  if (!isset ($end_at [$i])) continue;  // might be extra nodes in graph that are not in any edges
  for ($j = 1; $j < count ($end_at [$i]); $j++) {
    printf ("glue %s %s\n", $end_at [$i][0], $end_at [$i][$j]);
  }
}

?>
