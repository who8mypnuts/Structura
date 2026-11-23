#!/opt/local/bin/php
<?php

date_default_timezone_set ('America/Vancouver');

   
function doit ($com) {
  print "$com\n";
  system ($com);
}

foreach (glob ("*.eobj") as $eobj) {
  doit ("dos2unix $eobj");
}

?>
