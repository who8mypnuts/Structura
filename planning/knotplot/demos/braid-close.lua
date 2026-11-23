--[[
 
   rob scharein, 8-10 February 2023
 
--]]

if demo ~= luaSource then
  demo = luaSource
  Demo ()
  executeKP ([[
    reset all
    sradius = 0.3
    vscale = 0.16
    
    stusplit = 1
    
    alias r "lua . RandomBraid ($0)"
    show none
    txt on
    txt clobber on
    label-mode = 3     % shows only the component labels
    scenery off
    scenery dscale 0.5
    
    txt lineskip -25

    txt right
    txt font 3
    txt fill on
    txt font 4
    txt -14 14 ?
    txt font 3
    txt -15 a2 fullscreen "full toggle"
    txt -15 a labels "show ~labels"
    txt -15 a orientation "show ~orientation"
    txt -15 a scenery "scenery toggle"
    txt -15 a grid "show ~grid"
    txt -15 a projection "lua . ToggleProjection ()"
    txt -15 a mode "lua . ToggleMode ()"

    txt fill off
    txt -10 a toggle:
    
  ]])
  

  Title ("Closing Braids")
  require ("Vector3")
  
  perspective = true
  
  function ProclaimSafeness (extraText)
    if Safe () then
      Message (extraText .. ": safe")
    else
      Message (extraText .. ": not safe")
    end
  end
  
  function ToggleProjection ()
    if perspective then
      executeKP ("ortho")
    else
      executeKP ("persp")
    end
    perspective = not perspective
  end
  
  function ToggleMode ()
    mode = lcaptureKP ("mode")
    if mode [2] == "s" then
      executeKP ("mode cb")
    else
      executeKP ("mode s")
    end
  end
  
  function CycleTopKnot ()
    topKnotIndex = topKnotIndex + 1
    if topKnotIndex > #topKnots then
      topKnotIndex = 1
    end
  end
  
  topKnots = explode (" ", "top0a top0a top0b top1a top1b top2a")  -- topKnots and offset should
  offset   = explode (" ", "14 10 10 14 14 14")                    -- have the same number of entries
  topKnotIndex = 1
  
end  -- end of run once section

executeKP ([[
  delete all
  go 0
  scenery delete
  
  txt font 3
  txt left
  txt fill on
  txt 15 15   "change top" "lua . CycleTopKnot ();lua run braid-close"
  txt 15 a1.5 ID "lua . GetID ('jidknot')"
  txt 15 a  "connect" "join all; lua . ProclaimSafeness ('connect'); txt delete connect"
  txt 15 a  "add lines" "lua . Lines (); txt delete add"
  txt 15 a   "rerun demo" "lua run braid-close"
  txt fill off
  txt 10 a action:
  
  txt push
  txt lineskip 25
  
  alias m  "lua . Message ('')"
  alias rb "lua . RandomBraid ($0)"
  alias b  "braid -strings 3 $0"
  alias sdo "scenery delete;scenery on"
  alias ~calc "lua . Title ('calculating...')"
  
  txt fill off
  txt 10 -77 "step by step:"
  txt fill on
  txt 15 a    RandomBraid    "go 0;m;rb \ri[1/11];sdo"
  txt 15 a    BigRandomBraid "go 0;m;rb \ri[12/55];sdo"
  txt 15 a    AddArcs        "m;lua . AddArcs ();sdo"
  txt 15 a    Top            "m;lua . Top ();sdo"
  txt 15 a    FindEndPoints  "m;lua . FindEndPoints ()"
  txt 15 a    Lines          "m;lua . Lines ()"
  txt 15 a    connect        "m;load |l;join all; lua . ProclaimSafeness ('connect');
  txt 15 a    ID             "~calc;lua . GetID ('jidknot')"
  txt 15 a    "ID L12"       "~calc;lua . GetID ('jidknotL12')"
  txt 15 a    "ID K12"       "~calc;lua . GetID ('jidknotK12')"

  txt pop
]])

function GetID (jidknotVersion)
  executeKP ([[
    Drawing = false
    silent = true
    ago 33
    Drawing = true
    gauss _tmp.egc
    silent = false
  ]])
  --print ("jhomfly _tmp.egc | " .. jidknotVersion .. " -- -k > _tmp.id")
  os.execute ("jhomfly _tmp.egc | " .. jidknotVersion .. " -- -k > _tmp.id")
  local f = assert (io.open ("_tmp.id", "r"))
  local t = f:read ("*all")
  f:close ()
  Title ("ID is " .. t)
  executeKP ("panel draw")
end

function Message (message)
  if message == "" then
    EphemeralMessage_yPos = -55
    return
  end
  
  EphemeralMessage (message)
  EphemeralMessage_yPos = EphemeralMessage_yPos - 24
end

Message ("")
  
function Translate (deltaX, deltaY, deltaZ, componentNumber)
  executeKP ("translate " .. deltaX .. " " .. deltaY .. " " .. deltaZ .. " " .. componentNumber)
end

function RandomBraid (numGenerators)
  -- creates a braid and saves to internal file |rp

  local braidWord = ""
  for i = 1, numGenerators do
      braidWord = braidWord .. chooseKP ("a b A B") 
  end
  
  local padding = ""
  if numGenerators == 1 then
    padding = " 0^2 "
  elseif numGenerators == 2 then
    padding = " 0 "
  end
  local comm = "braid -strings 3 " .. padding .. braidWord .. padding
  executeKP (comm)

  Message (comm)
  
  executeKP ([[
    scale 0.5
    about z 90
    save |rb
  ]])
  
  Message (braidWord)
  Message (Plural (numGenerators, "generator"))
end

function AddArcs ()
  -- loads internal file |rb and saves to internal file |aa

  executeKP ("load |rb")
  
  local info = lcaptureKP ("info s")    -- returns a table with indexing starting at 1
  local xmin = info [6]
  local xmax = info [7]
  local ymin = info [8]
  local ymax = info [9]
  local zmin = info [10]
  local zmax = info [11]

  echoKP ("extent in x: " .. xmin .. " <---> " .. xmax)
  echoKP ("extent in y: " .. ymin .. " <---> " .. ymax)
  echoKP ("extent in z: " .. zmin .. " <---> " .. zmax)
  executeKP ("save |x")
  local r = info [9]

  executeKP ("unknot 22 " .. 2 * r)
  executeKP ("cut span x 0")
  Translate (xmin, r, 0, 1)
  Translate (xmax, r, 0, 0)
  executeKP ("load combine |x")
  executeKP ("save |x")
  executeKP ("unknot 22 " .. r .. "; cut span x 0")
  executeKP ("cut span x 0")
  Translate (xmin, r, 0, 1)
  Translate (xmax, r, 0, 0)
  
  -- add two short segments
  local segment = {}      -- each segment is a Lua table, create an empty table
  local delta = 0.4       -- the next two lines explicitly specify the keys 1 and 2
  segment [1] = Vector3.new (xmin + delta, ymax + delta, 0)
  segment [2] = Vector3.new (xmin + 2 * delta, ymax + 2 * delta, 0)
  addComponentKP (segment)
  
  segment = {}      -- next two lines are a different way to add points to a segment, equivalent to the above
  table.insert (segment, Vector3.new (xmax - delta, ymax + delta, 0))
  table.insert (segment, Vector3.new (xmax - 2 * delta, ymax + 2 * delta, 0))
  addComponentKP (segment)

  executeKP ([[
    load combine |x
    jthresh = 1
    join all
    safe
    save |aa
  ]])

  ProclaimSafeness ("add arcs")
end


function Top ()
  executeKP ("load " .. topKnots [topKnotIndex] .. ".k")
  Title (topKnots [topKnotIndex] .. " offset by " .. offset [topKnotIndex])
  Translate (0, offset [topKnotIndex], 0, "")
  executeKP ("load comb |aa;centre;save |t")
end


function FindEndPoints ()
  -- loads internal file |t and saves to internal file |fep
  
  executeKP ("load |t")
  
  -- create two empty tables
  leftPoint = {}
  rightPoint = {}

  for i = 1, paramKP ("ncomp") do
    local comp = getComponentKP (i - 1)  -- returns a table with indexing starting at 1
                                         -- KnotPlot indexes everything starting at 0
    local firstPoint = comp [1]
    local lastPoint = comp [#comp]
      
    if firstPoint.x < 0 then
      table.insert (leftPoint, firstPoint)
    else
      table.insert (rightPoint, firstPoint)
    end
  
    if lastPoint.x < 0 then
      table.insert (leftPoint, lastPoint)
    else
      table.insert (rightPoint, lastPoint)
    end

  end

  sortBy_yCoordinate = function (v1, v2)      -- nameless function receiving two points
                         return v1.y < v2.y   -- and sorting according to the y component
                       end
                      
  table.sort (leftPoint,  sortBy_yCoordinate)
  table.sort (rightPoint, sortBy_yCoordinate)

  colour = explode (" ", "red orange yellow green blue violet")
  for i = 1, #colour do
    sphere = string.sub (colour [i], 1, 1) .. "sphere"
    executeKP ("scenery object eobj/" .. sphere .. " " ..
         Vector3.String (rightPoint [i]))
    executeKP ("scenery object eobj/" .. sphere .. " " ..
         Vector3.String (leftPoint [i]))
  end
  
  executeKP ("save |fep")
end

RandomBraid (Random ("ri[1/11]"))
AddArcs ()
Top ()
FindEndPoints ()

function Line (a, b)
  local trim = 0.7
  local comm = "line from " .. a.x .. " " .. a.y .. " " .. a.z ..
                     " to " .. b.x .. " " .. b.y .. " " .. b.z ..
                     " trim " .. trim
  executeKP (comm)
end

function Lines ()
  -- loads internal file |fep
  
  executeKP ([[
    load |fep
    
    save |nolines
    delete all
    scenery delete
    new = false
  ]])
  
  Message ("")
  
  Line (leftPoint [1], leftPoint [4])
  Line (leftPoint [2], leftPoint [5])
  Line (leftPoint [3], leftPoint [6])
  Line (rightPoint [1], rightPoint [4])
  Line (rightPoint [2], rightPoint [5])
  Line (rightPoint [3], rightPoint [6])
  
  executeKP ([[
    new = true
    refine equilateral 1.5
    save |lines
    load |nolines
    load combine |lines
    save |l
    safe
  ]])

  ProclaimSafeness ("add lines")

end

