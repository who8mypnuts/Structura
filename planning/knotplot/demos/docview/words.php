txt push
txt delete group 108
txt centre
txt group 108
txt fill off

<?php

$essay = file_get_contents ("essay.txt");
$words = explode (" ", $essay);

$nwords = count ($words);
$nbeads = 200.0;

$nwords += 0.108;

$limit = 624;

$index = 0;

print "% number of words is $nwords, limited to $limit\n";

foreach ($words as $word) {
  $bead = $nbeads * ($index / $limit);
  printf ("txt bead %.3f \"%s\"\n", $bead, $word);
  $index++;
  if ($index > $limit) break;
}


?>

txt pop
