#!/usr/bin/php
<?php

date_default_timezone_set ('America/Vancouver');

   
function doit ($com) {
  print "$com\n";
  system ($com);
}

$kpb = 4691;

$files = glob ("*.kps");

foreach ($files as $file) {
  $stuff = file_get_contents ($file);
  if (substr_count ($stuff, "alias qfix") < 1) continue;
  print "$file\n";
  $stuff = str_replace ("alias qfix", "", $stuff);
  $fp = fopen ($file, "w");
  fprintf ($fp, "require KPbuild $kpb\n");
  fprintf ($fp, "%s", $stuff);
  fclose ($fp);
}


?>
