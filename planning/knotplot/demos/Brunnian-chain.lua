--[[

rob scharein
Saturday, 30-Dec-23 20:18:27 UTC

--]]

Demo ()

function RotateView ()
  if RollDie (3) == 1 then
    if RollDie (102) == 1 then
      executeKP ("rotate i \\rr[50/70]")     -- viewed from "below"
    else
      executeKP ("rotate i \\rr[-50/-70]")   -- viewed from "above"
    end
  end
end

if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    sradius = 0.265086
    vscale = 0.219977
    velforce = on
    label-mode = 3
    force 1
    #4 echo
    txt on
    txt clobber on
    txt fill on
    txt centre
    txt c 15 "rerun" "lua run Brunnian-chain nocolour"
    lua . RotateView ()
  ]])
  
  
  -- Create a string with the names of the Brunnian knot chains, separated by spaces
  -- and then use the chooseKP() function to choose one of them at random.
  -- Note we could also do this in the following way:
  --   brunnianKnot = "brunnian" .. Random ("ri[7/21]") .. ".k"
  -- which is simpler, but chooses each knot with the same probability.
  -- In this example, each knot is given a different probability of being chosen,
  -- with brunnian21 having half the chance of being picked than does brunnian7.
  --     rob scharein, january 2023

  brunnianKnots = ""
  probs = ""
  space = ""
  

  for i = 7, 21 do
    brunnianKnots = brunnianKnots .. space .. "brunnian" .. i .. ".k"
    probs = probs .. space .. (35 - i)
    space = " "
  end
  
  --echoKP ("choosing from the set of knots: " .. brunnianKnots)
  --echoKP ("with relative probabilities: " .. probs)
  
  require ("ColourUtils")
  
  verbose = true    -- not to be confused with the KnotPlot parameter

  function ToggleVerbose ()
    if verbose then
      --executeKP ("verbose = 0")
      ColourUtils.verbose = false
    else
      executeKP ("verbose = 1")
      ColourUtils.verbose = true
    end
    verbose = not verbose
  end

  ToggleVerbose ()
  
  firstcall = true
  method = "deleting"

end   -- end of init block

ButtonHelp ()
ButtonStack ('toggle:,labels,show ~labels,draw mode,lua . ToggleDrawingMode(),' ..
             'animation,lua . ToggleAnimation (),verbose,lua . ToggleVerbose(),fullscreen,full toggle')
ButtonStack ("phantom unlink|action:,unlink,lua . Unlink ()")
ButtonStack ("select on,group 102|method:,open,lua . setMethod ('opening'),delete,lua . setMethod ('deleting')")

ButtonAutoHide (5, 6)
  
brunnianKnot = chooseKP (brunnianKnots, probs)

executeKP (brunnianKnot, [[
  echo
  load ARG1
  about z \rr360
  <randorient.kps
  hstart = \rr360
  panel draw
  %drag = true  causes problems if a hover bead is below a txt button
  go
]])
animating = true

Title ("Brunnian Chain with " .. paramKP ("ncomps") .. " components")
SubTitle ("rerun demo to get a different number of components")


colourSet = chooseKP ("burntorange,purple|red,orange,yellow,green,cyan,blue,magenta|cerulean,cyan|off", "1|1|1|11", "|")
if verbose then print (colourSet) end

if #arg > 0 then
  if arg [1] == "nocolour" then
    colourSet = "off"
  end
end

colourSet = "off"   -- I don't like the colouring schemes, keep this off until something better comes along

if colourSet == "off" then
  --executeKP ("colour off")
else
  --ColourUtils.ColourFromSet (colourSet)
end


function setMethod (which)
  method = which
  EphemeralMessage ("will unlink by ", method, "one component")
end

function ToggleAnimation ()
  if animating then
    executeKP ("go 0")
  else
    executeKP ("go")
  end
  animating = not animating
end

function ToggleDrawingMode ()
  if captureKP ("mode") == "mode s" then
    executeKP ("mode cb")
  else
    executeKP ("mode s")
  end
end

function Unlink ()
  if method == "opening" then
    executeKP ([[
      open 0
      echo opened a component
    ]])
  elseif method == "deleting" then
    executeKP ([[
      % translate component so it's far offscreen
      % this way we don't have to worry about the colours
      translate 99999 0 0 0    % translate component 0 (it doesn't matter)
      echo deleted a component
    ]])
  end
  
  executeKP ([[
    txt push
    txt phantom unlink
    txt replace "unlink" "rerun" "lua run Brunnian-chain"
    txt pop
  ]])
 
end

if firstcall then
  executeKP ([[
    txt click delete
  ]])
  firstcall = false
end

ShowSourceButton ()
requireKPbuild (5064)

--[[

BEGIN HELP

Brunnian links inspired by the exercise on page 69 of Dale Rolfsen's `Knots and Links'.

This demo creates a chain of similar Brunnian links, up to a fairly high number of components.
These links can be unlinked on one of two ways:
    --- delete a component
    --- open a component by cutting the string
Choose between these two methods using the "delete" and "open" buttons. Then click on the "unlink"
button to run an animation of the unlinking.

Use either "rerun" button to create a new Brunnian chain. For convenience, the "unlink" button
changes into a "rerun" button when you click on it (and then back to "unlink"). This makes
it easy to unlink many consecutive chains by just repeatedly clicking in the same place.

Every now and then the components will be coloured in a non-standard way. If you prefer just
the standard colouring, use the "rerun" button at the bottom of the screen instead of the
one in the "action:" section. This is the only difference between using the two "rerun" buttons.







END HELP

--]]
