<?php

$essay = file_get_contents ("mt.txt");
$limit = 2500;
$nbeads = 1250.0;

$limit = $nbeads = 689;

$limit += 0.108;

for ($letter = 0; $letter < strlen ($essay); $letter++) {
  $bead = $nbeads * ($letter / $limit);
  printf ("txt bead %.3f \"%s\"\n", $bead, $essay [$letter]);
  if ($letter > $limit) break;
}


?>
