#!/usr/bin/php
<?php

foreach (glob ("*") as $thing) {
  
  $result = exec ("kpfsnoop $thing | grep IDEN");
  if ($result != "")
    print "$thing\n";

}

?>
