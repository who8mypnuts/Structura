--[[

rob scharein
Thursday, 14-Mar-24 16:15:24 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    mode cb
    sradius = 0.15
    ncur = 5
    txt on
    txt clobber on
    scenery on
    grsize = 20
    
    stusplit = 1
    
    function silent
    function 2 "lua . Wikipedia ()"
    function 3 "info"
    
    txt push
    txt group 42
    txt font 4
    txt centre
    txt expire 8
    txt c 100 "Note: crossings are computed by an orthographic projection to"
    txt c 75  "the xy-plane, use this toggle button to see the xy-plane --->"
    txt pop
  ]])

  Demo ()
  
  require ("Primitives")
  
  Title ("TSP Knots")
  SubTitle ("using a naive travelling salesperson algorithm")
  
  ButtonHelp ()
  ButtonStack ("toggle:"
           ..  ",draw mode,lua . ToggleDrawingModeTSP ()"
           ..  ",xy-plane,lua . ToggleXYplane ()"
           ..  ",fullscreen,fullscreen toggle"
              )
  ButtonStack ("action:"
           ..  ",create,lua . NewKnot ()"
           ..  ",relax,lua . Relax ()"
           ..  ",ID,lua . ID()"
              )
  ButtonStack ("select on,group 222|method:"
           ..  ",3D,lua . Create = Create3D;lua . smooth = false;lua . NewKnot()"
           ..  ",2D,lua . Create = Create2D;lua . smooth = false;lua . NewKnot()"
               )

  firstCall = true
  xyPlane = false
  smooth = false
  
end   -- end of init block

function Wikipedia ()
  executeKP ([[
    www en.wikipedia.org/wiki/Travelling_salesman_problem
  ]])
end

maxxings = 102

--[[

smooth   xyPlane   3D     mode
true     true      true   sS
false    true      true   cbS
true     false     --     s
false    false     --     cb

--]]

function ToggleDrawingModeTSP ()
  smooth = not smooth
  UpdateStuff ()
end
  
function UpdateStuff ()
  local m = ""
  if xyPlane and Create == Create3D then
    if smooth then
      m = "sS"
    else
      m = "cbS"
    end
  else
    if smooth then
      m = "s"
    else
      m = "cb"
    end
  end
  executeKP ("mode " .. m)
end

function UpdateStuff_wrong ()
  if smooth then
    executeKP ("mode sS")
  else
    executeKP ("mode cbS")
  end
end


function ToggleXYplane ()
  xyPlane = not xyPlane
  if xyPlane then
    executeKP ("show +grid")
    xyzAxes ()
  else
    executeKP ("show -grid;scenery delete")
  end
  UpdateStuff ()
end



function ID ()
  local nxings = tonumber (captureKP ("xing"))
  if nxings > maxxings then
    EphemeralMessage ("too many crossings (" .. nxings .. "), try relaxing")
  return
  end
  EphemeralMessage ("knot ID", "is", captureKP ("id"))
end

function BT ()
  local message = Plural (captureKP ("xing"), "crossing") .. ", " ..
                  Plural (paramKP ("nbead"),  "bead")
  BotTitle (message)
  echoKP (message)
end

function Relax ()
  BotTitle (" ")
  executeKP ("ago 111")
  BT ()
end

function Create3D ()
  executeKP ([[
    go 0
    set shadow 0
    silent = true
    random uniform \ri[66/777]
    align axes
    silent = false
    tsp
  ]])
end

function Create2D ()
  executeKP ([[
    go 0
    set shadow 1
    silent = true
    random uniform \ri[20/55]
    scale 1 1 0
    untran
    silent = false
    tsp
  ]])
end
 

function ReportStuff (theTimeTaken,
                      numberSteps, didTimeOut)
  EphemeralMessage (Plural (numberSteps, "tsp step"))
  executeKP ([[
    #4 echo
    safe
  ]])
  BT ()
end

function NewKnot ()
  BotTitle (" ")
  UpdateStuff ()
  DoUntil (Create, Safe, 4, ReportStuff)
end

if firstCall then
  firstCall = false
  executeKP ("txt click 3D")
end

NewKnot ()

ShowSourceButton ()

requireKPbuild (5064)

--[[

BEGIN HELP

Things to try:

   -- Click the `create' button to create a new knot.
      KnotPlot will keep creating knots until it finds
      one that is a `safe' position (use the `safe'
      command to check knot safeness). KnotPlot will
      display how many tsp steps it took.
      
   -- If the knot has too many crossings, try relaxing a bit with
      the `relax' button. The number of crossings is computed using
      an orthographic projection to the xy-plane. This is usually
      different than the number of apparent crossings in the current view.
      
   -- Click on the `ID' button to identify the currently loaded knot,
      it must have 102 crossings or fewer when projected to the xy-plane.

This demo uses the `tsp' command in KnotPlot, a naive implementation of
the travelling salesperson problem (TSP). Note, this algorithm creates
a rather coarse approximate to the minimal length path. To see how bad
(or not so bad) it is, change the method to `2D'.

Press F2 to go to the Wikipedia page on the travelling salesperson problem.




END HELP

--]]
