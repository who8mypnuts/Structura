--[[

Using the cut command

rob scharein, 15 April 2022

modify Cylinder to have different radii at top and bottom
can be use to draw cones
options for filling the ends
use this to draw the normal vector to the cutting planes
also put labels "inside" and "outside"!

--]]


require "Primitives"

if demo ~= luaSource then
  Demo ()
  demo = luaSource
  executeKP ([[
    reset all
    txt push
    txt left
    txt fill on
    txt 15 -40 "drawing mode" "lua . toggleDrawingMode ()"
    txt pop
    txt centre
    txt clobber on
    cyl-rad = 0.4
    scenery on
  ]])

  Title ("Using the cut command")
  BotButton ("reload demo", "lua run cut2")
  call = 1
  cutModes = {"span", "in", "out"}
end


function InsideOutsideLabels (pointInPlane, normal, axis)
  if axis == string.upper (axis) then mult = -1 else mult = 1 end
  posOut = Vector3.add (pointInPlane, Vector3.mult (normal, 4 * mult))
  posIn =  Vector3.sub (pointInPlane, Vector3.mult (normal, 4 * mult))
  executeKP ("txt push;txt font 6;txt delete group 77;txt group 77")
  executeKP ("txt " .. Vector3.value(posOut) .. " outside")
  executeKP ("txt " .. Vector3.value(posIn)  .. " inside")
  executeKP ("txt pop")
  norm = Vector3.normalized (Vector3.sub (posOut, pointInPlane))
  Arrow (pointInPlane, norm, 2.5, 102, "yellow")
end


cutMode = cutModes [Random ("ri[1/3]")]
-- cutMode = "span"

sweepTime = Random ("rr[0.5/7]")
last = 11


--last = 4 sweepTime = 13

CutSweep = coroutine.create (
function ()
  executeKP ([[
    save |original
    txt push
    txt font 4
  ]])
  
  if FlipCoin () then
    axis = "x"
    normal = Vector3.xhat
  else
    axis = "y"
    normal = Vector3.yhat
  end
  if FlipCoin () then axis = string.upper (axis) end

  first = -last
  if FlipCoin () then
    first = -first
    last = -last
  end

  startTime = timeKP ()
  endTime = startTime + sweepTime;
  
  repeat
    executeKP ("load |original;scenery delete")
    p = (timeKP () - startTime) / sweepTime
    value = Interpolate (first, last, p)
    executeKP ("refine 11")
    com = "cut " .. cutMode .. " " .. axis .. " " .. string.format ("%.03f", value)
    executeKP (com)
    executeKP ("refine equi")
    executeKP ('txt c 40 "' .. com .. '"')
    pointInCutPlane = v3.mult (normal, value)
    Plane (pointInCutPlane, normal, 11, 2, "orange", 0.4, true)
    InsideOutsideLabels (pointInCutPlane, normal, axis)
    
    executeKP ([[
      %hincr = 0
      display true
      echo -f
      nap 0.05
    ]])
    coroutine.yield ()
  until p >= 1.0
  executeKP ("txt pop")
end
)

function step ()
  if coroutine.status (CutSweep) == "dead" then   -- happens when coroutine has finished
    executeKP ([[
      load |original
      idle
      scenery delete
      txt delete group 77
    ]])
  else
    coroutine.resume (CutSweep)
  end
end

executeKP ([[
  knot
  fitto 10.7
]])

executeKP ('idle "lua . step ()"')

call = call + 1

function toggleDrawingMode ()
  if tcaptureKP ("mode") [1] == "s" then
    executeKP ("mode cb;cyl-rad = 0.12")
  else
    executeKP ("mode s;cyl-rad = 0.4")
  end
end

ShowSourceButton ()


