--[[

modified from dance1.kps demo

it's more like swimming than dancing!

rob scharein, 31 January 2023

--]]

require "Primitives"
require "Animate"

Demo ()

require "ColourUtils"
require "Dynamics"
speed = Dynamics.speed

RequireKLE (13)


executeKP ([[
  reset all
  idle -cpi off  % added 12 August 2024, KPbuild 5067
  silent = true
  sradius = 0.3
  cradius = 0.6   % for use with mode q
  coll a
  force 1
  velf = true
  tanf = true
  alias ~l "line numb \ri[$0/$1];line dir \rr+-1 \rr+-1 \rr+-1;line"
  vscale = .18
  dstep = 11
  rotate x \rr360
  rotate y \rr360
  rotate z \rr360
  
  3dop line width 11
  
  label-mode = 3
  itsave = true
  sformat = 1
  
  sphere luxo 7
  sphere on
  mathsv S 240 1 1 d
  mathsv S 0 0 0 s
  alpha S 0.8
  sphere 19
  %if \rr100 < 11 then "show sphere" else "show none"
  % now prefer to hide sphere by default
  show none
  silent = false

  new = false
  alias cfs "lua . ColourUtils.ColourFromSet ('$0')"

  alias ~clast "colour last hsv:$0/$1/$2"
  alias ~kolour "colour $0 hsv:$1/$2/$3"
  alias ~em  "txt group 0 off;tfunction 2 {play \ri[33/55];lua . EMessage();~qm} 0 rep 300 600"
  alias ~emo "txt group 0 on"
  alias ~si "lua . StringInfo ()"
  alias ~qm "tfunc 2.22 {lua . Qmop ()}"
  alias speed "lua . speed('$0')"
  alias sp "lua . spinners ()"
  alias -e rcb "txt group path on;lua relax relaxCallback"

  alias ~u "silent=t;unknot \ri[17/25] \rr[1/2];project random last;translate \rr+-16 \rr+-16 \rr+-16 last;~clast \rr360 \rr[0.7/1] \rr[0.75/1];open all;silent=f"

  vcn = 1
  vcphi = 3.14159
  vcA = 1
  
 
  txt fill on
  txt centre
  txt font 3
  txt c 20 "reload demo" "lua run swim"
  txt clobber on
  
  txt lineskip -25

  % mode q uses the qslabs material (formerly arrow material) and
  % qmoption slaspect VALUE  (default is 0.125)
  alias ~q "mathsv q \rr360 \rr[.8/1] 1 d"

  fscale = 365
  ascale = 0.0155
  
  txt on
  
  tfunction 11 "lua . ReverseOneComponent ()" 0 rep 5 15
  alias -e c "lua . CheckForSpinners ()"
  alias -e sc "tfunc 1 c 0 rep 6"
  
  scenery on
  
  lua do inventory
  
  tfunction \rr[55/111] "lua . BeginTransitioning ()"
  
  alias -e iter "lua . iter()"
  tfunction 102.2 "lua . iter ()"  0 rep 10m 30m
  
  timer start
]])

function iter ()
  local p = lcaptureKP ("par iter")[3]   -- gets the number of iterations as a string
  local s = commify (p)
  echoKP (captureKP ("timer check") .. '  ' .. s .. ' iterations')
  print (p, s)
end

ButtonHelp ()
ButtonStack ('toggle:,ips,show ~ips,labels,show ~labels,sphere,show ~sphere,motion blur,lua . ToggleMotionBlur(),animation,lua . ToggleAnimation(),' ..
             'fullscreen,full toggle')

ButtonStack ("select on,group 108|background:,black,lua . SetBackground ('black'),ocean,lua . SetBackground ('ocean'),grey,lua . SetBackground ('KnotPlotGrey'),white,lua . SetBackground ('white')")

-- have to be careful with the different quotes, the following doesn't work:
--ButtonStack ('background:,black,lua . SetBackground ("black"),ocean,lua . SetBackground ("ocean"),grey,lua . SetBackground ("KnotPlotGrey"),white,lua . SetBackground ("white")')

ButtonStack ('action:'
         ..  ',hide,lua . Hide ()'
         ..  ',jitter,jitter 99999;fitto 0.1'
         ..  ',recolour,lua . ReColour()'
         ..  ',inventory,lua . StringInfo ()'
         ..  ',autohue,lua . StartTransition()'
         ..  ',check,speed')
  
ButtonStack ('select on,group path|path:'
         ..  ",first,lua . pathWhat = 'first'"
         ..  ",last,lua . pathWhat = 'last'"
         ..  ",cofm,lua . pathWhat = 'cofm'"
            )
executeKP ('txt group path off')


ButtonStack ("left")

executeKP ('txt push;txt fill off;txt 15 .01 " ";txt pop')

ButtonStack ("select on,group 109|drawing mode:,smooth,mode s;sradius=0.3,beads,mode b;bradius=0.67,beads & cyls,mode cb;cradius=0.1;bradius=0.2,q-slabs,mode q;cradius=1.2;~q,lines,mode l,forces,mode f")

ButtonStack ("change:,open/close,open toggle,reverse,revbeads,split,split")
ButtonStack ("delete:,long,reap long 10,short,reap short 10,all,reap all")
ButtonStack ("new string:,long,lua . LongString(),short,lua . ShortString(),bunch,lua . Bunch()")

ButtonAutoHide (5,6)

pathClosed = true

function relaxCallback (which)
  if which ~= 1 or paramKP ("ncomp") < 2 then return end
  local points = Vector3.getEndpoints (pathWhat)
  if #points < 2 then return end
  executeKP ("scenery delete")
  CylinderPath (points, 0.15, 3, "white", pathClosed)
end

function BeginTransitioning ()
  executeKP ([[
    echo starting transitions...
    tfunc 2 "lua . StartTransition()" 0 rep 40 70
  ]])
end


function Qmop ()
  local upDir = captureKP ("qmop up random")
end

function SetBackground (option)
  if option == "ocean" then
    executeKP ([[
      show +back
      drop all 52 35 -20
      drop ca black
      drop cb black
      drop cc #116
      drop cd #116
    ]])
    return
  end
  executeKP ("show -back;background = " .. option)
end

function ReverseOneComponent ()
  local ncomps = paramKP ("ncomps")
  if ncomps < 7 then return end
  executeKP ("revbeads " .. Random ("ri" .. (ncomps - 1)))
end

showSpeedKount = 0

spthresh = 0.9  

function spinners (p)
  if p == nil then
    speed (0)
  
    executeKP ([[
      tfunc 1 "lua . spinners(0)"
      echo call 1
    ]])
  else
   local hue = 0
   local sat
   local value

   for k,v in pairs (Dynamics.speedTable) do
     sat = 1 - (v [2] - Dynamics.speedMin) / (Dynamics.speedMax - Dynamics.speedMin)
     value = sat
     local com = "noop"
     if sat < spthresh then com = "hide" end
     echoKP (string.format ("%d %.2f %.2f  %.2f", k - 1, v [1], v [2], sat))
     executeKP (k - 1, hue, sat, value, com, [[
       %echo colour ARG1 hsv:ARG2/ARG3/ARG4
       %colour ARG1 hsv:ARG2/ARG3/ARG4
       ARG5 ARG1
      ]])
    end
    executeKP ('tfunction 5 "unhide all"')
  end
end

function showSpeed ()
  showSpeedKount = showSpeedKount + 1
  if showSpeedKount < 9 then
    echoKP ("checking speeds...")
  end
  
  EphemeralMessage ("component centre of mass speeds:",
  string.format ("average %.2f, min %.2f (%d), max %.2f (%d)",
                                 Dynamics.speedAverage,
                                 Dynamics.speedMin, Dynamics.speedCompmin,
                                 Dynamics.speedMax, Dynamics.speedCompmax))
  if #Dynamics.speedTable > 8 then
    return
  end
  for k,v in pairs (Dynamics.speedTable) do
    echoKP (string.format ("%d %.2f %.2f", k - 1, v [1], v [2]))
  end
end

Dynamics.speedCallback (showSpeed)

indexHide = 3
function Hide ()
  if indexHide == 3 then
    indexHide = 1
  else
    indexHide = indexHide + 1
  end
  --print (indexHide)
  
  executeKP ("unhide all")
  if indexHide == 3 then EphemeralMessage ("unhiding all strings") return end
 
  local fun = function (C, N) if N > 10 then executeKP ("hide " .. C) end end
  local which = "long"
  
  if indexHide == 1 then
    fun = function (C, N) if N < 10 then executeKP ("hide " .. C) end end
    which = "short"
  end
  
  EphemeralMessage ("hiding " .. which .. " strings")
  
  lengthInfo = mlcaptureKP ("length")
  numStrings = paramKP ("ncomps")
  for s = 1, numStrings do
    numBeads = lengthInfo [s + 1][3]
    fun (s - 1, tonumber (numBeads))
  end
end

function Bunch ()
  executeKP ("delete all")
  for i = 0, Random ("ri[16/33]") do
    if FlipCoin () then
      ShortString ()
    else
      LongString ()
    end
  end
  executeKP ([[
    jitter 999999
    fitto 1.02
  ]])
  StringInfo ()
end

function NewString (minB, maxB)
  executeKP ("~l " .. minB .. " " .. maxB)
  local ncomps = paramKP ("ncomps")
  
  ColourComponent (ncomps - 1, minB)
  EphemeralMessage (Plural (ncomps, 'string'))
  executeKP ("unhide all")
  indexHide = 3
end

function IncrHue (hincr)
  local hsvinfo = mlcaptureKP ("info -full ih")
  for i = 1, #hsvinfo do
    local c = hsvinfo [i][1]
    local hsv = string.sub (hsvinfo [i][2], 5, -1)
    local e = explode ("/", hsv)
    local hue = tonumber (e [1])
    --print ("component " .. c .. " has hue " .. hue)
    executeKP (i - 1, e [1] + hincr, e [2], e [3], [[
      colour ARG1 hsv:ARG2/ARG3/ARG4
    ]])
  end
end

function StartHueChange (incr, interval)
  executeKP (incr, interval, [[
    tfunction ARG2 "lua . IncrHue (ARG1)" 0 rep ARG2
  ]])
  EphemeralMessage ("incrementing hues by " .. incr .. " every " .. interval .. " seconds")
end

function AutoHue ()
  StartHueChange (1, 55)
end

function ShortString ()
  NewString (4, 6)
end

function LongString ()
  NewString (17, 25)
end

function ColourAll (how)
  for c = 1, paramKP ("ncomps") do
    local r = Random (how)
    local g = Random (how)
    local b = Random (how)
    executeKP (r, g, b, c - 1, [[
      colour ARG4 rgb:ARG1/ARG2/ARG3
    ]])
  end
  executeKP ("info -full ich")
end

function Dark ()
  ColourAll ("rr.02")
end

function Bright ()
  ColourAll ("rr[.8/1.0]")
end

--  \rr360 \rr[0.7/1] \rr[0.75/1]   for long
--  \rr360 \rr[0.9/1] \rr[0.9/1]    for short

satLongHi = explode (" ", "1 0 1 0 1")
satLongLo = explode (" ", "0.7 0 1 0 1")
valLongHi = explode (" ", "1.0 0.9 1 0.75 1")
valLongLo = explode (" ", "0.7 0.6 1 .5 1")

satShortHi = explode (" ", "1 1 0 0 0")
satShortLo = explode (" ", "0.9 1 0 0 0")
valShortHi = explode (" ", "1.0 1 0.9 1 0")
valShortLo = explode (" ", "0.9 1 0.6 0.75 0")

indexSatVal = 1

function ColourComponent (comp, nBeads)
  hue = Random ("rr360")
  if nBeads > 10 then
    sat = Random ("rr[" .. satLongLo [indexSatVal] .. "/" ..
                           satLongHi [indexSatVal] .. "]")
    val = Random ("rr[" .. valLongLo [indexSatVal] .. "/" ..
                           valLongHi [indexSatVal] .. "]")
  else
    sat = Random ("rr[" .. satShortLo [indexSatVal] .. "/" ..
                           satShortHi [indexSatVal] .. "]")
    val = Random ("rr[" .. valShortLo [indexSatVal] .. "/" ..
                           valShortHi [indexSatVal] .. "]")
  end
    
  executeKP ("~kolour " .. comp .. " " .. hue .. " " .. sat .. " " .. val)
end

function ReColour ()
  if indexSatVal == #satLongLo then
    indexSatVal = 1
  else
    indexSatVal = indexSatVal + 1
  end
  -- print ("\n\nrec " .. indexSatVal)
  lengthInfo = mlcaptureKP ("length")
  numStrings = paramKP ("ncomps")
  for s = 1, numStrings do
    numBeads = lengthInfo [s + 1][3]
    ColourComponent (s - 1, tonumber (numBeads))
  end
end

cofmPrev = {}    -- table of Vector3

function CheckForSpinners ()
  local stuff = mlcaptureKP ("info -full m")
  local cofmNow = {}
  for i = 1, #stuff do
    cofmNow [i] = Vector3.new (stuff [i][1], stuff [i][2], stuff [i][3])
  end
  --executeKP ("info -full m")
  if #cofmPrev == #cofmNow then
    executeKP ("scenery init;scenery on;scenery vscale 4")
    local found = false
    
    for i = 1, #cofmPrev do
      local length = Vector3.distance (cofmPrev [i], cofmNow [i])
      if length < 3 then
        executeKP ("echo " .. i - 1 .. ": " .. string.format ("%.2f", length) .. ' ')
        --Cylinder (cofmPrev [i], cofmNow [i], 0.2, 12, "blue")
        executeKP ('scenery object eobj/wire-icosahedron ecomp ' .. i - 1)
        found = true
        --executeKP ('scenery object eobj/gsphere ecomp ' .. i - 1)  spheres have a lot of faces
      end
    end
    if found then executeKP ("#2 echo") end
  end
  cofmPrev = cofmNow
end

animating = false

function Frames (nframes)
  -- make an animated GIF using ImageMagick!     https://imagemagick.org
  -- convert -delay 4 -loop 0 __swim*png out.gif
  
  for i = 1, nframes do
    executeKP (string.format ("__swim%05d", i - 1), [[
      ago 3
      fitto sphere 20
      lximgout ARG1 5 256
      echo lximgout ARG1 5 256
    ]])
  end
end

function ToggleAnimation ()
  if animating then
    executeKP ("idle")
  else
    executeKP ('idle "ago 3;fitto sphere 20"')
  end
  animating = not animating
end

inTransition = false

inTransition_func = nil
inTransition_comp = 0
inTransition_hue0 = 0
inTransition_sat0 = 0
inTransition_val0 = 0
inTransition_val1 = 0
inTransition_T0 = 0
inTransitionRate = 22  -- degrees per second
inTransitionDeltaHue = 30
inTransitionDirection = 1
inTransitionDuration = 2

function Transition1 ()
  if not inTransition then return end
  local t = (timeKP () - inTransition_T0) / inTransitionDuration
  if t > 1 then
    Transition()
    return
  end
  local s = Animate.easeInOutQuad (t)
  local hueChange = Interpolate (0, inTransitionDeltaHue, s) * inTransitionDirection
  local newHue = inTransition_hue0 + hueChange
  local sat = Interpolate (inTransition_sat0, 1, s)
  local val = Interpolate (inTransition_val0, inTransition_val1, s)
  --print (t .. " " .. s .. " " .. newHue)
  executeKP (newHue, sat, val, inTransition_comp, [[
    colour ARG4 hsv:ARG1/ARG2/ARG3
  ]])
end

trs = 0.3   -- transition sphere scale

function StartTransition ()
  if inTransition then
    --echoKP ("currently in transition")
    return
  end
  --print ("\n\n")
  inTransition_comp = Random ("ri" .. (paramKP ("ncomps") - 1))
  --echoKP (inTransition_comp)
  --executeKP ("display true;echo -f;nap 5")

  --inTransition_comp = 3
  inTransition_func = Transition1
  local hsv = explode (" ", captureKP ("info -full h " .. inTransition_comp))
  --print ("hsv:")
  --printTable(hsv)
  --echoKP (hsv [1])
  inTransition_hue0 = tonumber (hsv [1])
  inTransition_sat0 = tonumber (hsv [2])
  inTransition_val0 = tonumber (hsv [3])
  inTransition_val1 = Random ("rr[0.4/1]")
  --print (string.format (">%f,%f,%f<", inTransition_hue0, inTransition_sat0, inTransition_val0))
  inTransitionDeltaHue = Random ("rr[60/180]")
  inTransitionDirection = 1
  inTransition_T0 = timeKP ()
  local e_or_b = "e"
  if FlipCoin () then
    inTransitionDirection = -1
    e_or_b = "b"
  end
  inTransitionDuration = inTransitionDeltaHue / inTransitionRate
  
  executeKP (inTransition_comp, e_or_b, trs, [[
    scenery push
    scenery vscale ARG3
    scenery object eobj/wsphere ARG2comp ARG1
    scenery pop
  ]])

  Transition ()
end


function Animalt ()
  executeKP ([[
    ago 3
    fitto sphere 20
  ]])
  if inTransition_func ~= nil then
    inTransition_func ()
  end
end

function Transition ()
  if inTransition then
    executeKP ([[
      idle "ago 3;fitto sphere 20"
      %echo using normal animation
      scenery delete
    ]])
    --print ("n")
  else
    executeKP ([[
      idle "lua . Animalt()"
      %echo using alternate animation
    ]])
    --print ("a")
  end
  inTransition = not inTransition
end

NewString (17, 25)
ToggleAnimation ()

function EMessage ()
  executeKP (captureKP ("timer check"), [[
    txt push
    txt fill off
    txt font 4
    txt expire \rr[3/4]
    txt centre
    txt c c "running for ARG1"
    txt pop
  ]])
end

function StringInfo ()
  local s, l = Inventory (10)
  EphemeralMessage (" ")
  EphemeralMessage (Plural (s, "short string"),
                    Plural (l, "long string"),
                    Plural (l + s, "string") .. " total")
end

function ToggleMotionBlur ()
  executeKP ([[
    if accbuffon then "accbuff off" else "accbuff decay 0.980730;accbuff accum 0.217651;accbuff return 0.225359;back=#000;accbuff on;accbuff clear"
  ]])
end

function testint ()
  local t = explode (" ", "1 2 3.4 reset .3 .5m .5h .5d 3.5m 4.5h 4S 2.5M 1D 2.3w")
  for i = 1, #t do
    local s = captureKP ("test int " .. t [i])
    --print (">" .. t [i] .. "< " .. s)
  end
end

executeKP ([[
  txt clickon grey
  txt clickon smooth
  txt clickon first path
]])

requireKPbuild (5092)  -- for commify function in Demos()

--[[

Ideas:

  attach lights to the small strings
      
  detect spinners and mark them somehow
  
BEGIN HELP







END HELP

--]]
