#!/usr/bin/php
<?php

date_default_timezone_set ('America/Vancouver');

   
function doit ($com) {
  print "$com\n";
  //system ($com);
}

foreach (glob ("?c_*") as $k) {
  $j = str_replace ("_", ".", $k);
  doit ("cp $k $j");
}

?>
