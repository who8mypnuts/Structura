#!/usr/bin/php
<?php
print "% KnotPlot\n";    // all constructors must print this first



if ($argc < 7) {
  print "echo Usage: cons eric HIGHCOLOUR LOCOLOUR START STOP\n";
  print "% no temp files\n";
  return;
}

$tbase = $argv [1];      // basename for temporary files created by KnotPlot during construction
$call = $argv [2];       // an integer 0, 1, 2 ... 0 for first call, 1 for second call, etc.
$infofile = "$tbase.info";

$colour_highlight = $argv [3];
$colour_lowlight = $argv [4];


$start = 8 * $argv [5];
$stop = 8 * $argv [6] - $start;

if ($call == 0) {        // true upon first time KnotPlot calls this constructor
  print "par nbeads > $infofile\n";
  print "colour all $colour_highlight >> $infofile\n";
  print "colour all $colour_lowlight >> $infofile\n";
  print "close = 0\n";           // to avoid any problems not being able to split
  print "save |x\n";
  print "#3 split\n";
  print "shift -$start\n";

  print "% run again\n";   // signal to KnotPlot to run the constructor again
  return;
}

//system ("cp $infofile dum");

$stuff = explode ("rgbi:", file_get_contents ($infofile));
list ($ignore, $nb) = explode ("nbeads = ", $stuff [0]);
list ($nbeads) = explode ("\n", $nb);

list ($hi) = explode ("'", $stuff [1]);
list ($lo) = explode ("'", $stuff [2]);

list ($hir, $hig, $hib) = explode ("/", $hi);
list ($lor, $log, $lob) = explode ("/", $lo);

print "echo nbeads is $nbeads hi is $hir $hig $hib and lo is $lor $log $lob\n";

$PPMfile = "$tbase.ppm";

$expand = 4;

$nrows = min (8192, $nbeads * 8 * $expand);
$stop *= $expand;

$fp = fopen ($PPMfile, "w");
fprintf ($fp, "P6\n1 $nrows\n255\n");
for ($i = $nrows - 1; $i >= 0; $i--) {
  if ($i >= 0 && $i < $stop) 
    $colour = pack ("CCC", $hir, $hig, $hib);
  else
    $colour = pack ("CCC", $lor, $log, $lob);
  fprintf ($fp, $colour);
}
fclose ($fp);

//system ("cp $PPMfile dum.ppm");

print "colour all white\n";    // needed for the texture mapping 

print "tex norm $PPMfile\ndraw tex\ntex rep 1 1\ntex on\n";

?>
