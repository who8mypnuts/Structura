--[[

rob scharein
Monday, 2024 August 12, 17:04:38 PDT

--]]

click = ""
space = ""

for i = 1, #arg do
  click = click .. space .. arg [i]
  space = " "
end

--if demo ~= luaSource then
if true then
  demo = luaSource
  executeKP ([[

reset all
alloc 19999
alias ~ah "txt hide \rr[5/7]"


silent=t
verbose=f

func init
func silent
txt clobber on
alias ~setname "~ah;txt push;txt font 4;txt left;txt fill off;txt 10 -20 { };txt set name;txt pop"

alias ~lki "echo;echo;echo;echo idea for this demo from Lou Kauffman"

alias ~pu "tangle push;tg1offset = 3;echo -n {turning };tangle padding on;echo making tangle..."
alias ~po "tangle pop;tangle padding;echo -n {number of crossings is };xing"

alias ~unk "~lki;alias ~lki nop;~pu;Draw=f;tangle ($0,$1,$2,$3)($0,$1,$2)z#;ago 33;Draw=t;name {tangle ($0,$1,$2,$3)($0,$1,$2)z#     <--- numbers are randomly chosen (click again)};~po"

alias ~newknot "idle;go 0;~setname;txt delete hint;drag=f;par3=0;txt delete group 102;untran;save |.tmp;<split-delete-aux2.kps"
 
alias ~delmany "delete down 5;delete rrob"
alias ~relaxnorm "txt delete relax;idle;go;txt c 20 {relax and simplify} <split-delete-aux.kps"

alias ~c "echo;echo;echo"

alias ~lsknot "~c;load LigSeth$0;~newknot"
alias ~raor "<randorient.kps"

txt on
txt fill off
txt left
txt font 4
txt lineskip 25
txt colour white .8
txt 10 -60 "Knot zoo:"
txt font 2
txt fill on

txt fcolour royalblue .6

txt 20 a "LigSeth0" "~lsknot 0"
txt 20 a "LigSeth1" "~lsknot 1"
txt 20 a "LigSeth2" "~lsknot 2"

txt 20 a "Monster1" "~c;load Monster.k;~newknot"
txt 20 a "Monster2" "~c;load NotMonster.k;~newknot"
txt 20 a "bigunknot" "~c;load bigunknot;~newknot;par3=1;~raor"
txt 20 a "birman"  "~c;load birman2.k;~newknot;~raor"
txt 20 a "hard unknot" "~c;load hard-unknot1.k;~newknot;~raor"
txt 20 a "Haken unknot"  "~c;load haken.k;~newknot;~raor"
txt 20 a "Goeritz unknot"  "~c;load goeritz.k;~newknot;~raor"
txt 20 a "MT unknot" "~c;load mt-unknot.k;~newknot;~raor"
txt 20 a "111 xing" "~c;load LewGanBru1.k;~newknot;~raor"
txt 20 a "complex T(2,7)" "~c;load LewGanBru2.k;~newknot;~raor"
txt 20 a "unknot ?" "~c;~unk \ri[-5/5] \ri[-5/5] \ri[-5/5] \ri[-5/5];~newknot"
txt 20 a "42 xing" "~c;load 42.k;~newknot;~raor"
txt 20 a "complex hopf" "~c;load complex_hopf1.k;~newknot;~raor"
txt 20 a "unknot A" "~c;load nasty-unknotA.k;~newknot"
txt 20 a "unknot B" "~c;load nasty-unknotB.k;~newknot"

txt 20 a "Figure-8" "~c;load nasty-fig8A.k;~newknot"
txt 20 a "15 xing" "~xing 15"
txt 20 a "19 xing" "~xing 19"
txt 20 a "22 xing" "~c;load lissa-0_1.k;~newknot"
txt 20 a "31 xing" "~xing 31"

txt 20 a "crazy braid" "~c;go beadlimit 3000;load crazy-braid.k;~newknot"
txt 20 a "figure-8" "~c;load fig8-sat4.k;~newknot"
txt 20 a "11mar04a" "~c;load 11mar04a.k;~newknot"
txt 20 a "11mar04b" "~c;load 11mar04b.k;~newknot"

alias ~xing "~c;load $0xing-unknot.k;~newknot"
~ah

txt fill on
txt cent
%txt c 20 "reload demo" <split-delete.kps

txt right
txt lineskip -25

~ah

txt font 4
txt fill on
txt -14 14 ? "help popup split-delete.kps handoff"
txt font 3

~ah

alias ~togglemode "if \ppar4 == 0 then {par4=1;mode s} else {par4=0;mode cb}"


txt -15 a1.5 fullscreen "full toggle"
txt -15 a  "draw mode" ~togglemode
txt fill off
txt -10 a toggle:
txt fill on

~ah

txt -15 a3 centre centre
txt -15 a  "enable dragging"  "drag=t;~relaxnorm;par4=1;~togglemode;echo;echo;echo click on a bead and drag it"
txt fill off
txt -10 a action:


mode cb
%hstar=200
%ccmode=2
cradius = 0.15
sradius = 0.4
bradius = 0.21
vscale = 0.3
dbmin=5
%<randorient2.kps  % removed 24 July 2020
rotate z \rr360
rotate y \rr360
rotate x \rr360

%centre mass
%fixcofm=t  %too distracting!


<split-delete-aux2.kps

~ah

txt autohide on   % should be the last txt command

silent=f

echo
echo
echo " *** click on `begin simplification' to simplify the knot"
echo "     or use one of the buttons to load a different knot"
echo

func 2 "www knotplot.com/thesis"


  ]])


  firstcall = true

end   -- end of init block

if click ~= "" then
  executeKP (click, [[
    txt click "ARG1"
    %txt click "begin simplification"
    vscale = 0.12
    mode s
  ]])
end

--[[

BEGIN HELP

For information on how this knot simplification works, see Section 7.3.3
of my dissertation "Interactive Topological Drawing".

Press F2 now to go to a web page where you can download a copy.

Goeritz Hard Unknot from paper "Hard Unknots and Collapsing Tangles" by
Louis H. Kauffman and Sofia Lambropoulou.

unknot ? demo from idea of Lou Kauffman.


END HELP

--]]
