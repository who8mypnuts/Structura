% Demo of `mangle' command.

% To remake this script, run 
% php mangle-demo.php > mangle-demo.kps

require KPbuild 4350

reset all


func init
func silent
func 1 <mangle-demo.kps

echo 
echo 
echo "  *** Demo of crankshaft rotations (KnotPlot `mangle' command)"
echo "      Use view window buttons to try different options for `mangle'"
echo 

verbose=f

scale = .35
stusplit = 1

cyl = .14
bead=.18
mode cB

txt init

txt centre
txt font 4
txt c -20 "Crankshaft Rotations";
txt font 3 
txt c a "using the KnotPlot `mangle' command";
txt left

txt font 3
txt fcolour royalblue .6
txt fill on

<?php

$x = 20;
$y = 15;
$yincr = 28;


$mangles = array (
'mangle 555 180 1 1 1' => 'mangle 555 times',
'mangle 102 180 1 1 1' => 'mangle 102 times',
'mangle 20 180 1 1 1' => 'mangle 20 times',
'mangle 1 180 1 1 1' => 'mangle once',
'mangle 555 5 1 1 1' => 'mangle 555 times',
'mangle 102 5 1 1 1' => 'mangle 102 times',
'mangle 20 5 1 1 1' => 'mangle 20 times',
'mangle 1 5 1 1 1' => 'mangle once',
'mangle 20 90' => ' ',
'mangle 1 90' => ' '
);

$creations = array (
'torus 2 3 \ri[10/40]' => ' ',
'torus 2 3 22' => ' ',
'unknot \ri[4/20] 6' => ' ',
'unknot 10 6' => ' '
);


foreach ($mangles as $mangle=>$explain) {
  print "txt $x $y \"$mangle\" \"$mangle;centre\"\n";
  $y += $yincr;
}

$y += 5; $x -= 6;
print "txt fill off\ntxt font 4\ntxt $x $y \"Then mangle it:\"\n";

$y += 10 + $yincr; $x += 6;

print "txt fill on\ntxt font 3\n";

foreach ($creations as $create=>$explain) {
  print "txt $x $y \"$create\" \"$create\"\n";
  $y += $yincr;
}

$y += 5; $x -= 6;
print "txt fill off\ntxt font 4\ntxt $x $y \"First create something:\"\n";



?>

txt space _
if \rr22 < 1 then "txt fill off;txt font 2;txt c 10 mangling_stuff_is_fun"

txt right
txt fill on
txt font 3
txt -15 40 "rerun this demo" <mangle-demo.kps
txt -15 15 "run another mangle demo" <mangle-demo2.kps
txt on
verbose=t
