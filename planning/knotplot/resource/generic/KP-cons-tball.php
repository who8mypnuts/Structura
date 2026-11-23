#!/usr/bin/php
<?php


  /*

KnotPlot constructor to add a "tangle ball" (a disc centered at origin and under the knot diagram)

Example Usages

to see usage information from within KnotPlot:
cons tball    

write to file `gumby.eps' knot diagram with a
tangle ball of radius 7 with default colour (75% gray):
cons tball gumby 7

write to file `pokey.eps' knot diagram with a
tangle ball of radius 6.3 and gray value of 32%
cons tball pokey 6.3 0.32

write to file `sveegee.eps' knot diagram with a
tangle ball of radius 12.2 and a RGB colour of (.3, .83, .21):
cons tball sveegee 12.2 .3 .83 .21

rob scharein, 31 December 2012

   */

date_default_timezone_set ('America/Vancouver');

   
function doit ($com) {
  print "echo $com\n";
  system ($com);
}

// define some constants
$outline_mode_values    = 1;
$outline_mode_component = 2;
$outline_mode_knotfile  = 3;

$outline_mode = $outline_mode_values;

print "% KnotPlot\n";

$tempbase = $argv [1];
$call = $argv [2];
$orig_eps = "$tempbase-back.eps";
$rgbvalues = "$tempbase-colours";
$path = "$tempbase-path.txt";

if ($argc < 5) {
  print 'echo "Usage: cons tball FILENAME TBALL"' . "\n";
  print 'echo "       cons tball FILENAME TBALL GRAYVALUE"' . "\n";       
  print 'echo "       cons tball FILENAME TBALL RED GREEN BLUE"' . "\n";
  print 'echo "       where GRAYVALUE, RED, GREEN and BLUE are in [0,1]"' . "\n";
  print 'echo "       cons tball FILENAME TBALL NAMEDCOLOUR"' . "\n";       
  print 'echo "       TBALL is one of: RADIUS  WIDTH/HEIGHT  WIDTH/HEIGHT/ANGLE  cCOMPONENT  OUTLINE.k' . "\n";
  system ("touch $tempbase");
  exit ();
}

$outfile = basename ($argv [3], ".eps") . ".eps";

if (substr_count ($argv [4], ".k") > 0) 
  $outline_mode = $outline_mode_knotfile;
else if ($argv [4][0] == 'c') {
  $outline_mode = $outline_mode_component;
  $comp = str_replace ("c", "", $argv [4]);
  if ($comp == "") 
    $comp = 0;
}

if ($call == 0) {
  print "silent=t\nparsave\n";
  switch ($outline_mode) {
  case $outline_mode_component:
    print "save |tmp\n";
    print "keep $comp\nsave $path\n";
    print "load |tmp\ndelete $comp\n";
    break;
  case $outline_mode_knotfile:
    print "save |tmp\n";
    printf ("load %s\nsave $path\n", $argv [4]);
    print "load |tmp\n";
    break;
  }
  print "psout $orig_eps\n";
  switch ($outline_mode) {
  case $outline_mode_component:
    print "load |tmp\n";
    break;
  }
  print "parres\nsilent=f\n";
  if ($argc > 5 && !is_numeric ($argv [5])) {
    $name = $argv [5];
    print "echo looking up `$name' to find:\n";
    print "colour -lookup \"$name\" > $rgbvalues\n";
  }
  print "% run again\n";
  exit ();
}


if ($outline_mode == $outline_mode_values) {
  
  $rotate = 0;
  
  if (substr_count ($argv [4], "/") == 1) 
    list ($xsize, $ysize) = explode ("/", $argv [4]);
  else if (substr_count ($argv [4], "/") == 2) 
    list ($xsize, $ysize, $rotate) = explode ("/", $argv [4]);
  else
    $xsize = $ysize = $argv [4];
  
  
  if ($xsize <= 0.0 || $ysize <= 0.0) {
    print "echo absurd value for one or more parameters\n";
    exit ();
  }
}

if ($argc == 6) {
  if (is_numeric ($argv [5]))
    $colour = sprintf ("%f %f %f", $argv [5], $argv [5], $argv [5]);
  else {
    list ($r, $g, $b) = explode (" ", file_get_contents ($rgbvalues));
    if ($g == "***") {
      //print "echo invalid colour name found\n";
      exit ();
    }
    $colour = sprintf ("%f %f %f", $r, $g, $b);
  }
}
else if ($argc == 8) 
  $colour = sprintf ("%f %f %f", $argv [5], $argv [6], $argv [7]);
else
  $colour = "0.75 0.75 0.75";

$colourdef = sprintf ("/thickC {%s setrgbcolor} def\nthickC\n", $colour);

$insert = "Begin data\n\n$colourdef\n";

if ($outline_mode != $outline_mode_values) {
  $insert .= "newpath\n";
  $command = "moveto";
  foreach (explode ("\n", rtrim (file_get_contents ($path))) as $point) {
    
    if ($point == "") {
      $insert .= "closepath\n";
      $command = "moveto";
    }
    else {
      list ($x, $y) = explode (" ", $point);
      $insert .= "$x $y toPS $command\n";
      $command = "lineto\n";
    }
  }
  $insert .= "closepath gsave fill grestore clip\n";
}
else {
  $insert .= "psXoff psYoff translate\n$rotate rotate\n$xsize $ysize scale\n";
//$insert .= "newpath 0 0 psScale 0 360 arc fill\nnewpath 0 0 psScale 0 360 arc clip\n";
  $insert .= "newpath 0 0 psScale 0 360 arc gsave fill grestore clip\n";
  $insert .= "1 $xsize div 1 $ysize div scale\n$rotate neg rotate\npsXoff neg psYoff neg translate\n\n";
}

list ($stuff1) = explode ("showpage", file_get_contents ($orig_eps));
list ($ignore, $stuff2) = explode ("Begin definitions",
				   $stuff1);



//doit ("cp $orig_eps orig.eps");

$fp = fopen ($outfile, "w");
fprintf ($fp, "%s\n%s\n",
	 str_replace (array ($orig_eps, basename ($orig_eps)), 
		      array ($outfile, $outfile), $stuff1),
	 str_replace ("Begin data", $insert, $stuff2));
fprintf ($fp, "\n\nshowpage\ngrestore\ngrestore\n");
fclose ($fp);

print "echo Postscript written to file `$outfile'.\n";

?>
