#!/usr/bin/php
<?php

// a KnotPlot constructor to ID knots on the simple cubic lattice, given a knot file


// a constructor should always print out this string
print "% KnotPlot\n";

// all constructors are called with the following two parameters filled in automatically
$temp = $argv [1];   // name of a temporary file (or basename for temporary files)
$run = $argv [2];    // calling sequence, 0, 1, 2 ...

$egcfile = "$temp.egc";

if ($run == 0) {
  print "silent=t\nsave |tmp\n";
  print "% run again\n";

  print "Draw=f\nago 108\ndele down 6\nago 108\nalign axes\ngauss a\ngauss $egcfile\n";
  print "load |tmp;Draw=t\n";
  return;
}

// if we get here, $run is 1 or more

$knot = exec ("filter-egc.php < $egcfile | homfly -- | idknot -- -k");

if ($knot == "0.2.1a") {
  print "txt init\n";
  print "idle\nscenery off\ntxt init\ntxt font 4\ntxt cent\ndbmin=5\n";
  //print "tfunc 1 \"del down 10\" 0 rep .5\nstus=1\n";
  print 'bindkey d "dele down -4";';
  print 'bindkey g "<relax.kps";';
  print "func 1 <recombo.kps\nfunc 2 del down -4\n";
  //print "bindkey \" \" go\n";

  print "txt clobber on\ntxt cent\ntxt font 4\ntxt c -60 $knot\ntxt on\n";
  print "txt c -20 \"direct recombination\"\n";
  print "alias ~doit nop\n";
}
print "silent=f\necho $knot\n";

print "txt push\ntxt clobber on\ntxt cent\ntxt font 4\ntxt c -60 $knot\ntxt pop\n";


?>
