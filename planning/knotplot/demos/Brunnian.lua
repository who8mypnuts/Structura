Demo ()

moviesLoaded = captureKP ("movie clist")

if demo ~= luaSource then
  call = 1
end
demo = luaSource

if moviesLoaded ~= "b backward forward" then
  executeKP ([[
  reset all
  vscale = 0.23
  silent = true
  movie load Brunnian6.kpm b
  movie atend b "lua . Finish ()"
  movie load Brunnian6.kpm forward
  movie load Brunnian6.kpm backward
  movie atend forward "movie rplay backward"
  movie atend backward "movie play forward"
  silent = false
  drop all 52 35 -20
  rotate unit
  rotate x -60
  ]])
end

executeKP ([[
  movie stop

  if stereo then "background = black" else "show back"
  drop ca black
  drop cb black
  drop cc midnightblue
  drop cd midnightblue
  rotate z \rr360
  
  txt init
  txt font 4
  txt colour #ffa500
  txt clobber on
  
  txt centre
  txt c 108 "Six Component Brunnian Link"
  txt on

  txt font 3
  
  txt fill on
  txt fcolour #00a .6
  txt fcolour royalblue .5

  txt c 80 "run animation" "txt delete group 108;txt delete run;movie play"
  hstart = \rr360

  load Brunnian6.k

  display true
  
  #4 echo
  echo This demo rewritten in Lua on 29 March 2022!
  echo
  echo " *** Click on the `run animation' button"
  echo
  ncur = 3
  nseg = 12
  sradius = 0.3

]])

if call == 1 then
  executeKP ([[
  txt fill off
  txt group 108
  txt c 40 "From page 67 of `Knots and Links' by Dale Rolfsen"
  txt c 20 "Publish or Perish, c1976"
  txt group 0
  ]])
end
call = call + 1


function Relax ()
executeKP ([[
select init
select off
txt init
txt clobber on

dstep = 4
stusplit=5

nap .4

dbmin=5

%play init
alias ~p "if compsep then {idle;go 66;txt delete One;txt delete Othe;txt group 9 on;play 84}"

idle "ago 3;del down -4;~p"

par1=0
txt font 3
txt centre
txt colour #ffa500
txt c 55 "One string deleted, now simplifying..."
txt c 40 "Other five strings should fall apart"
txt group 9
txt fill on
txt fcolour royalblue .5
txt c 20 "play back and forth" ~bf
txt fill off
txt font 4
txt c 108 "Components separated!"
txt group 0
txt on
txt group 9 off


alias ~bf "txt delete all;movie rplay backward;~bft;lua . buttons ()"
alias ~bft "txt font 3;txt c 40 {you can rotate or scale the view using the mouse};txt c 20 {while this animation is occurring}

echo
echo
echo "  *** One string deleted, now simplifying..."
echo

]])
buttons ()

end

function Finish ()
executeKP ([[
select init
% we don't actually delete a component, just move it out of the way
% this allows us to not bother recolouring the components
select action 0 "click to delete" "translate 1000000 0 0 0;lua . Relax()"
select action 1 "click to delete" "translate 1000000 0 0 1;lua . Relax()"
select action 2 "click to delete" "translate 1000000 0 0 2;lua . Relax()"
select action 3 "click to delete" "translate 1000000 0 0 3;lua . Relax()"
select action 4 "click to delete" "translate 1000000 0 0 4;lua . Relax()"
select action 5 "click to delete" "translate 1000000 0 0 5;lua . Relax()"
select on

silent = false
Draw = true
echo
echo
echo "Click down on one of the strings to delete it"
echo
txt fill off
txt c 80 "A `Brunnian link' is a non-trivial link that"
txt c 65 "becomes trivial if one string is removed."
txt c 40  "Test this by clicking on one of the strings"
txt c 25 "to delete that string and start relaxing.

play 84
]])
end

ShowSourceButton ()

function buttons ()
  ButtonHelp ()
  ButtonStack ('toggle:'
            .. ',draw mode,lua . ToggleDrawingMode()'
            .. ',fullscreen,full toggle'
              )
  --ButtonAutoHide (5,6)
end

buttons ()



--[[

BEGIN HELP

A `Brunnian link' is a non-trivial link that
becomes trivial if one string is removed.
Test this by clicking on one of the strings
to delete that string and start relaxing.

This link is from page 67 of `Knots and Links' by Dale Rolfsen
Publish or Perish, (c) 1976

Be sure to run the `BruChain' demo to see
Brunnian links with an arbitrary number of crossings.




END HELP

--]]
