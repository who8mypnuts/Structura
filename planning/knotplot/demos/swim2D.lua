--[[

rob scharein, 26 november 2023

modified from dance2.kps

--]]

executeKP ([[
  reset all
  txt on
  txt clobber on
    
  verbose = 0
  sradius = 0.13
  vscale = 0.338860

  new = false
  vcn = 1
  vcphi = 3.14159
  vcA = 1

  tfunction 1.02 "lua . Reverse()" 0 repeat .5 1.02
    
  background = black
  
  txt centre
  txt fill on
  txt c 30 "rerun demo" "lua rerun"
    
  alias cfs "lua . ColourUtils.ColourFromSet ('$0')"

  
  function 2 "www github.com/delfrrr/delaunator-cpp/tree/master"
  
  

]])

Demo ()
require "ColourUtils"

ButtonHelp ()
ButtonStack ('toggle:,draw mode,lua . ToggleDrawingMode(),motion blur,lua . ToggleMotionBlur(),' ..
      'animation,lua . ToggleAnimation (),fullscreen,full toggle')
ButtonStack ('action:,reverse,revbeads,untran,untran')
ButtonStack ('recolour:,swimmers,lua . RecolourSwimmers(),triangles,lua . RecolourDT()')
ButtonAutoHide (5, 5.7)

function NewSwimmer (y)
  -- swimmers start out as horizontal lines
  executeKP (y, [[
    line number \ri[4/12]
    line -4 ARG1 0  4 ARG1 0
  ]])
end

for ypos = -12, 12 do
  NewSwimmer (ypos)
end

--[[

add a follow component feature using either the eye or lookat command

the component being followed should not get told to reverse

since all the swimmers are equivalent, the one followed may as well be #1

things to try:
  change the colour of the triangulation lines midway thru drawing

--]]


followingSwimmer = 0    -- not used yet

function Reverse ()
  -- randomly choose a swimmer and reverse it
  local s = Random ('ri[1/' .. paramKP ("ncomps") - 1 .. ']')
  if followingSwimmer == s then
    --echoKP ("not reversing " .. followingSwimmer)
    return
  end
  
  executeKP (s, [[
    %echo revbeads ARG1
    revbeads ARG1
  ]])
end

executeKP ([[
  hstart = \rr360
  jitter .1
  scale 1 1 0    % flatten the swimming to a 2D plane
  
  unknot 102 13  % boundary of the `pool' in which the swimmers are
  swap rev       % reverses the order of the components
  hide 0         % hide the edge of the pool
  
  revbeads random
  about z \rr360
  
  rmass all 1
  rmass comp 0 0   % fix the pool boundary
  tanforce = on
  
  go
  
]])

function ToggleMotionBlur ()
  executeKP ([[
    if accbuffon then "accbuff off" else "accbuff decay 0.980730;accbuff accum 0.217651;accbuff return 0.225359;back=#000;accbuff on;accbuff clear"
  ]])
end

function ToggleDrawingMode ()
  if captureKP ("mode") == "mode s" then
    executeKP ("mode sD")
  else
    executeKP ("mode s")
  end
end

function M (test)
  executeKP (test, [[
    echo ARG1
    mode
  ]])
end

if RollDie (3) == 1 then ToggleDrawingMode () end  -- roll a 3-sided die

function RecolourSwimmers ()   -- should cycle thru different colouring modes
  executeKP ([[
    colour all random
  ]])
end

colour = explode (" ", "red orange yellow green cyan magenta white purple brown")

method = Random ("ri9999")

function RecolourDT ()
  if captureKP ("mode") == "mode s" then
    EphemeralMessage ("toggle draw mode to see the triangles")
  end
  
  echoKP (" ")
  echoKP ("command used to set the colour:")
  
  if method % 5 == 0 then
    local c = colour [Random ("ri[1/" .. #colour .. "]")]
    executeKP (c, [[
      echo set colD ARG1
      set colD ARG1
    ]])
  elseif method % 5 == 1 then
    local red = string.format ("%0.2f", Random ("rr1"))
    local green = string.format ("%0.2f", Random ("rr1"))
    local blue = string.format ("%0.2f", Random ("rr1"))
    executeKP (red, green, blue, [[
      echo set colD rgb:ARG1/ARG2/ARG3
      set colD rgb:ARG1/ARG2/ARG3
    ]])
  elseif method % 5 == 2 then
    local hue = string.format ("%0.0f", Random ("rr360"))
    local saturation = string.format ("%0.2f", Random ("rr[0.7/1]"))
    local value = string.format ("%0.2f", Random ("rr[0.6/1]"))
    executeKP (hue, saturation, value, [[
      echo set colD hsv:ARG1/ARG2/ARG3
      set colD hsv:ARG1/ARG2/ARG3
    ]])
  elseif method % 5 == 3 then
    local red = string.format ("%d", Random ("ri255"))
    local green = string.format ("%d", Random ("ri255"))
    local blue = string.format ("%d", Random ("ri255"))
    executeKP (red, green, blue, [[
      echo set colD rgbi:ARG1/ARG2/ARG3
      set colD rgbi:ARG1/ARG2/ARG3
    ]])
  elseif method % 5 == 4 then
    -- two equivalent ways to get a randomly chosen named colour:
    --executeKP (captureKP ("colour choose"), [[
    executeKP (RandomNamedColour (), [[
      echo set colD ARG1
      set colD ARG1
    ]])
  end
  
  method = method + 1
end

function RecolourDT2 ()
  executeKP ([[
    txt click triangles
    txt off
    tfunc 7 "txt on"
  ]])
end

animating = true

function ToggleAnimation ()
  if animating then
    executeKP ("go 0")
  else
    executeKP ("go")
  end
  
  animating = not animating
end


--[[

BEGIN HELP

Some open-ended "knots" swimming around in two dimensions.

What to do:

   --- toggle the draw mode to show a Delaunay triangulation of the bead locations
   
   --- toggle motion blur
   
All the beads remain in the xy plane.  You can rotate the view as usual, use the
untran button to get back to the unrotated view.

The code for creating the Delaunay triagulation is due to Vladi Bilonenko and can be found at
https://github.com/delfrrr/delaunator-cpp/tree/master
(press F2 now to go to this page)

Minor modifications to this code were made so it could work within KnotPlot.
The modified file can be found in the resource/src/delaunator sub-directory in the
KnotPlot distribution.

The code is distributed under the MIT license, please refer to the GitHub page for
complete information.

rob scharein
28 november 2023


END HELP


--]]
