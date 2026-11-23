#!/usr/bin/php
<?php
$stuff = <<<'GUMBY'

reset all

scenery on
scenery scale 5

txt on
txt font 2

txt clobber on


txt lineskip 27
txt fill on
alias ~poly "scenery delete all;scenery object eobj/$0;~loadit $0"

alias ~loadit "txt group 108;txt delete {<};txt font 2;txt c -45 {to load this object, use the command:};txt font 6;txt c -70 {scenery object eobj/$0};txt group 0"

alias qfix

txt fcolour royalblue .5

alias ~title "txt fill off;txt font 4;txt cent;txt c -20 $0"

alias ~knot "hstar=\rr360;cyl-rad=\rr[.2/.5];knot;fitto \rr[3/9]"

txt space @
txt push
txt group 108

GUMBY;

$fp = fopen ("../eobj-examples.kps", "w");

fprintf ($fp, "%%`-\n");

date_default_timezone_set ('America/Vancouver');
fprintf ($fp, "%% File auto-generated on " . date (DATE_RFC850) . "  DO NOT EDIT!!\n");
$cwd = getcwd ();

$hostname = str_replace (".local", "", exec ("hostname"));


fprintf ($fp, "%% by running the script `" . basename (__FILE__) . "' in $cwd on $hostname \n\n");


fprintf ($fp, "%s\n", $stuff);

$ystart = -20;
$yincr = 22;
$polys = glob ("*.eobj");
$y = $ystart;
$x = 10;
$split = count ($polys) / 2;
$index = 1;

$prevnest = false;

foreach ($polys as $poly) {
  $stuff = explode ("\n", file_get_contents ($poly));
  $names = explode ("# ", $stuff [0]);
  $name = rtrim ($names [1]);
  $name = str_replace (" ", "@", $name);
  $poly = str_replace (".eobj", "", $poly);

  if (substr_count ($name, "translucent") > 0)
    $trans = "~knot";
  else
    $trans = "dele all";

  if (!strncmp ($poly, "nested", 6)) 
    $isnest = true;
  else 
    $isnest = false;

  if ($isnest != $prevnest) {
    if ($isnest) 
      fprintf ($fp, "txt fcolour purple .5\n");
    else
      fprintf ($fp, "txt fcolour royalblue .5\n");
  }
  fprintf ($fp, "txt $x $y \"$name\" \"~poly $poly;~title $name;$trans\"\n");
  $y -= $yincr;
  if ($index++ > $split) {
    fprintf ($fp, "txt right\n");
    $y = $ystart;
    $x = -10;
    $split = 999999;
  }
  $prevnest = $isnest;
}

$stuff = <<<'POKEY'
txt fill off
txt cent 

txt c 20 "left mouse to rotate, right mouse to scale"

txt pop


alias ~hide "txt group 108 off;~hideshow show"
alias ~show "txt group 108 on;~hideshow hide"
alias ~hideshow "txt push;txt font 3;txt left;txt fill on;txt 10 10 {$0 stuff} ~$0;txt pop"
alias qfix

~show

txt lineskip -24

par0=0
alias ~wireframe "if par0 == 0 then {glop poly line;par0=1} else {glop poly fill;par0=0}"
alias qfix

par1=0
glop back t
alias ~backface "if par1 == 0 then {glop back f;par1=1} else {glop back t;par1=0}"
alias qfix

txt font 3
txt right
txt fill on
txt -10 60 fullscreen "full toggle"
%txt -10 a  backface ~backface
txt -10 a  wireframe  ~wireframe
txt fill off
txt -10 a toggle:

txt font 4
txt fill on
txt -14 14 ? "help popup eobj-examples.kps handoff"

txt fill off
txt cent

txt font 4
txt c c "<--- Click one of the buttons --->"

exit

%`+

examples

POKEY;

fprintf ($fp, "%s\n", $stuff);


fclose ($fp);

?>
