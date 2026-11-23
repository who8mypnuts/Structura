--[[

A classic KnotPlot demo re-written in Lua on 27 March 2022 when
KnotPlot is reaching an age of nearly 30 years (use the age command
in KnotPlot to find out how old it is). Because KnotPlot's native
scripting language is rather limited, this was really complicated
to implement and needed multiple files. The Lua version is
much easier to understand or change and resides in just one file.

--]]

Demo ()

moviesLoaded = captureKP ("movie clist")

if moviesLoaded ~= "trefoil unknot" then

  executeKP ([[
    reset all
    verbose=false
    ncur = 3
    nseg = 10
    cyl-rad = \rr[.4/.5]
    hstart = 22
    satu = .7
    mode s
    mathsv s 22 1 .3 e
    silent=true
    movie load Monster.kpm      unknot
    movie load NotMonster.kpm   trefoil
    movie time unknot  3
    movie time trefoil 3
    movie atend unknot "lua . Finish(0)"
    movie atend trefoil "lua . Finish(3)"
    silent=false
  ]])

end

executeKP ([[

% bring back the following?
%if \rr3 < 1 then "rotate x 180"
%if \rr2 < 1 then "rotate z 180"

scale=.27
drop all 52 35 -20

if stereo then "back=black" else "spec back"

drop ca black
drop cb black
drop cc #216
drop cd #216

]])

if FlipCoin () then      -- randomize which gets to be Unknown 1
  knot1 = "NotMonster.k"
  knot2 = "Monster.k"
  movie1 = "trefoil"
  movie2 = "unknot"
else
  knot1 = "Monster.k"
  knot2 = "NotMonster.k"
  movie1 = "unknot"
  movie2 = "trefoil"
end

secondCoin = FlipCoin ()
showing = 1

function Annote2 ()
  executeKP ([[
    txt font 3
    txt fill on
  ]])
    
  if showing == 1 then
    executeKP ([[
      txt c 60 "load Unknown1 again" "lua . Compare (1)"
      txt c 20 "compare to Unknown2" "lua . Compare (2)"
    ]])
  else
    executeKP ([[
      txt c 60 "load Unknown2 again" "lua . Compare (2)"
      txt c 20 "compare to Unknown1" "lua . Compare (1)"
    ]])
  end
  
 end

function Finish (which)
  executeKP ([[
    txt centre
    txt font 4
    txt fill off
  ]])
  
  if which == 0 then
    executeKP ([[
      ncur = 3
      refine nbead 20
      power = 2
      coll a
      Draw = true
      go 300
      txt c -100 "It's an unknot!"
    ]])
  else
    executeKP ([[
      txt c -100 "It's a trefoil!"
    ]])
  end
  
  Annote2 ()
end

function Annote ()
  executeKP ([[
  txt init
  txt clobber on
  txt fcolour RoyalBlue 0.7
  txt colour white
  txt font 4
  txt centre
  txt on
  txt c -30 "Guess the Knot Type!"
  ]])
  
  if secondCoin then
    executeKP ('txt c -55 "Unknot or Trefoil?"')
  else
    executeKP ('txt c -55 "Trefoil or Unknot?"')
  end
  
  executeKP ([[
  txt centre
  txt fill off
  txt font 4
  ]])
    
  if showing == 1 then
    executeKP ("load " .. knot1)
    executeKP ('txt c -100 "Unknown 1"')
    executeKP ("txt font 3")
    executeKP ('txt c 100 "click the button below for the answer, but first compare it to Unknown2"')
    executeKP ("txt fill on")
    executeKP ('txt c 20 "compare to Unknown2" "lua . Compare (2)"')
  else
    executeKP ("load " .. knot2)
    executeKP ('txt c -100 "Unknown 2"')
    executeKP ("txt font 3")
    executeKP ('txt c 100 "click the button below for the answer, but first compare it to Unknown1"')
    executeKP ("txt fill on")
    executeKP ('txt c 20 "compare to Unknown1" "lua . Compare (1)"')
  end
  
  executeKP ([[
  txt fill on
  txt c 60 "find out!" "lua . FindOut ()"
  txt on
  ]])
  
end

function Compare (toWhich)
  showing = toWhich
  Annote ()
end

function FindOut ()
  executeKP ([[
  txt delete click
  txt delete find
  txt delete compare
  ]])
  if showing == 1 then
    executeKP ("movie play " .. movie1)
  else
    executeKP ("movie play " .. movie2)
  end
end

Annote ()

executeKP ([[
echo
echo
echo This demo rewritten in Lua on 27 March 2022!
echo
echo -n "One of Unknown1 or Unknown2 is "
if \rr2 < 1 then "echo a trefoil, the other is an unknot." else "echo an unknot, the other is a trefoil."
echo "(which gets to be which is chosen randomly"
echo " each time you click the `guess knot' button)"
echo
]])


ShowSourceButton ()

