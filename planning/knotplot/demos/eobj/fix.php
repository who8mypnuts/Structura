#!/usr/bin/php
<?php

$fp = fopen ("face.eobj", "r");

while ($line = rtrim (fgets ($fp))) {
  list ($p, $a, $b, $c) = explode (" ", $line);
  if ($p == "f") 
    print "$p $a $b $c\n$p $b $a $c\n";
  else
    print "$line\n";
}

fclose ($fp);

?>
