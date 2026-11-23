#!/usr/bin/php
<?php

// a KnotPlot constructor to add labels to a knot diagram to illustrate the Extended Gauss Code

function label_pos ($x, $y, $r, $theta) {
  $theta = $theta * M_PI / 180.0;   // convert from degrees to radians
  return sprintf ("%f %f",
		  $x + $r * cos ($theta), 
		  $y + $r * sin ($theta));
}

// a constructor should always print out this string
print "% KnotPlot\n";

// all constructors are called with the following two parameters filled in automatically
$temp = $argv [1];   // name of a temporary file (or basename for temporary files)
$run = $argv [2];    // calling sequence, 0, 1, 2 ...

$fontsize = 18;
$fontname = "Helvetica";

$show_orientation_bottom = false;

// parameters specified on the KnotPlot command line start here
if ($argc > 3) 
  $fname = $argv [3];
else 
  $fname = "example";

for ($index = 4; $index < $argc; $index++) {   // process optional arguments
  if ($argv [$index] == "bot")                 // indicate start of knot and orientation at bottom
    $show_orientation_bottom = true;
}

$gcode_file = "$fname.tex";    // a TeX file because we want to include it in our LaTeX file
$epsf_temp  = "$temp.eps";     // a temporary EPS file we edit to get the final 
$epsf_final = "$fname.eps";    // this is the final EPS file we keep and use for a figure in our document
$xing_file  = $temp;           // file with crossing information (sign, x, y and angle)

if ($run == 0) {    // when constructor is called for the first time, $run equals 0
  // write out some KnotPlot commands 
  print "silent=t\n";                 // keep KnotPlot silent for a while
  if ($show_orientation_bottom) {
    print "save |.temp\n";            // save current knot to internal file to be restored later
    print "translate to 0 0 0\n";     // move bead 0 to location (0, 0, 0)
  }
  print "psout $epsf_temp\n";         // write out the EPS to a temporary file (deleted automatically upon completion)
  print "dowker -info $xing_file\n";  // write out the crossing information to temporary file (also deleted)
  print "gauss $gcode_file\n";        // write out gauss code
  print "% run again\n";              // tell KnotPlot to call the constructor one more time
  if ($show_orientation_bottom)       // restore original knot
    print "load |.temp\n";
  print "silent=f\n";
  exit ();
}

// if we get here, $run is 1 or more

// replace the name of the temporary EPS file with the name of our final EPS file
$epsforig = str_replace (basename ($epsf_temp), $epsf_final, file_get_contents ($epsf_temp));

// read the gauss codes into an array (we loose the + and - data, but this doesn't matter)
$gcode = explode ("+", str_replace ("-", "+", rtrim (file_get_contents ($gcode_file))));

$insert = "\n% begin insert\n\n0 setgray\n\n";    // a string we're going to insert into the temp EPS file
                                                  // to get the final EPS file


$insert .= "/fontsize $fontsize def\n/$fontname findfont fontsize scalefont setfont\n\n";

$insert .= <<<GUMBY

/label {
  toPS
  moveto
  dup
  stringwidth
  pop
  2 div
  neg fontsize 3 div neg rmoveto 
  show
} def

GUMBY;

$xings = explode ("\n", rtrim (file_get_contents ($xing_file)));

$line_num = 0;       // line number of the crossing info file
foreach ($xings as $xing) {
  if (++$line_num < 3) continue;   // skip the first two lines in the crossing file
  list ($dtcode, $sign, $ignore1, $ignore2, $ignore3, $ignore4, $xc, $yc, $zc, $angle) =
    explode (" ", str_replace ("  ", " ", $xing));

  $label = $gcode [$line_num - 3];  // label on crossing (a1, b3, d2 and so on)
  if ($sign == 1)
    $sign_label = "+";
  else 
    $sign_label = "-";

  $angle *= 180.0 / M_PI;    // convert to degrees
  
  if ($label [0] == "a") {   // sufficient to write out labels for only the overcrossings
    $nlabel = str_replace ("a", "", $label);  // get rid of the "a" to get the numerical label
    //$comment = "% $dtcode $sign $label $nlabel angle=$angle";
    $comment = "";
    $insert .= "($sign_label) " . label_pos ($xc, $yc, 1.0, 0.0 + $angle) . " label  $comment\n";
    $insert .= "($sign_label) " . label_pos ($xc, $yc, 1.0, 180.0 + $angle) . " label  $comment\n";
    $insert .= "($nlabel) " . label_pos ($xc, $yc, 1.0, 90.0 + $angle) . " label  $comment\n";
    $insert .= "($nlabel) " . label_pos ($xc, $yc, 1.0, 270.0 + $angle) . " label  $comment\n";
  }
}

if ($show_orientation_bottom) 
  $insert .= "(start -->) 1 -.6 label\n\n";

$insert .= "\n% end insert\n\n";

$fpout = fopen ($epsf_final, "w");
fprintf ($fpout, "%s", str_replace ("% z=10", $insert, $epsforig));
fclose ($fpout);		 

print "echo \"EPS file written to `$epsf_final' and TeX code to `$gcode_file'\n";

?>
