#!/usr/bin/php
<?php

function errorExit ($info) {
  print "echo *** $info\n";
  print "% no temp files\n";  // print this line if there are no temporary files to be removed
  exit ();
}

print "% KnotPlot\n";

$tempbase = $argv [1];
$call = $argv [2];

$ppm = $tempbase;
$winfo = $tempbase . ".kps";
$cwdInfo = $tempbase . "-cwd.txt";     // needed thanks to macOS Catalina
$nameInfo = $tempbase . "-name.txt";

$filename = "knot-pict";    // default file name of final image
$tile = 9;     // renders $tile X $tile number of tiles of size equal to current view window size
$height = 900; // default height of final luxo-quality image

switch ($argc) {
 case 6:
   $height = $argv [5];  // fall-thru
 case 5:
   $tile = $argv [4];
 case 4:
   $filename = $argv [3];
}


if ($height < 10 || $height > 10000) 
  errorExit ("absurd value of $height for image height");

if ($tile < 2 || $tile > 18) 
  errorExit ("absurd value of $tile for number of tiles per row/col");

$cwd = getcwd ();    // no longer reliable under macOS Catalina
                     // now it SOMETIMES returns the correct directory, but often returns empty string

print "echo upon call $call: cwd is `$cwd'\n";
$png = "$cwd/$filename.png";

if (strlen ($filename) > 2 &&  file_exists ($png))
  errorExit ("file `$png' already exists");

if ($call == 0) {
  print "silent = t\n";
  print "sbuff\n";
  print "winfo $winfo\n";
  print "silent = f\n";
  print "cwd > $cwdInfo\n";
  print "name > $nameInfo\n";
  print "imtile $ppm $tile\n";
  print "% run again\n";
  print "dbuff\n";
  print "silent = f\n";
  exit ();
}

// upon call 1 is where the value of $cwd actually matters
// see how it compares with the value written by KnotPlot

list ($ignore, $KPcwd) = explode ("'", str_replace ("`", "'", file_get_contents ($cwdInfo)));
if ($KPcwd != $cwd) {
  print "echo ***** `$cwd' != `$KPcwd', using `$KPcwd'\n";
  $cwd = $KPcwd;
}

if ($filename == "\\n") {
  $fn = rtrim (file_get_contents ($nameInfo));
  if ($fn == "knot is not named")
    $filename = "noname";
  else
    $filename = $fn;
}

//$copyright = "-font MyriadPro-Bold -fill rgba\(44,44,44,0.35\) -pointsize 25 -gravity SouthWest -annotate +20+20 \"© 2019 Rob Scharein\"";

$annotate = "";
//$annotate = $copyright;

// create an optional file `annotate.txt' if you want to put a label or copyright notice on the image
if (file_exists ("annotate.txt")) {
  foreach (explode ("\n", rtrim (file_get_contents ("annotate.txt"))) as $ann) 
    $annotate .= "$ann ";
}

$dpi = 72;    // resolution of final image in dots per inch

$convertExecutableLocation = "/opt/local/bin";   // MacPorts on a Mac
$convertExecutableLocation = "/usr/bin";         // typical Linux, might also be /usr/local/bin


$comm = $convertExecutableLocation . "/convert $ppm.ppm -resize x$height $annotate -units PixelsPerInch -density $dpi \"$png\"";
print "echo $comm\n";

system ($comm);
//system ("open  \"$png\"");
print "echo PNG image written to file `$png'\n";

$stuff = explode ("\n", file_get_contents ($winfo));
list ($ignore, $ignore, $owidth, $oheight) = explode (" ", $stuff [2]);
$theight = $tile * $oheight;
$twidth = $tile * $owidth;

if ($theight < $height) {
  list ($fwidth, $fheight) = getimagesize ($png);
  print "echo *** warning: tiled dimensions ($twidth x $theight) smaller than final dimensions ($fwidth x $fheight)\n";
}

?>
