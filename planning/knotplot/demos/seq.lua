
if demo ~= luaSource then
  demo = luaSource
  Demo ()
  RequireKLE (8)
  --EphemeralMessage_yPos = -44
  
  executeKP ([[
    reset all
    mode cb
    rotate x -60
    alias oseq "lua . OpenSeq ('$0')"
    txt on
    txt clobber on
    jthresh = 1.02
    3dop oscale 0.2
    3dop ostep  3
    vscale = 1.1
    stusplit = 1
    scenery on
    scenery dscale 0.2
    txt fill on
    txt font 4
    txt left
    txt fill on
    
    txt 15 15 Mark "lua . Mark ()"
    txt R 15 Close "lua . Close ()"
    txt R 15 ID   "lua . ID ()"
  ]])
  
  require "Primitives"
  
end

Title ("Knot Sequences")

function OpenSeq (seqname)
  executeKP ("idle")
  result = lcaptureKP ("sequence open " .. seqname)
  if result [1] == "***" then
    EphemeralMessage ("couldn't open " .. seqname)
    return
  end
  
  View ()
end

function ShowIt ()
  BotTitle ("knot #" .. knotNumber .. ", " .. paramKP ("nbeads") .. " beads, rog = " .. captureKP ("rog"))
  executeKP ([[
    centre
    display true   % forces redisplay
    echo -f        % same as display true but for Command Window

    nap 0.1
    save |last
  ]])
end

function GetNext ()
  local stuff = lcaptureKP ("sequence +")
  if stuff [1] == "end" then
    --print ("ending...")
    return true
  end
  
  knotNumber = knotNumber + 1
  return false
end


function Finish (timeTaken, numSteps, didTimeOut)
  local message = string.format ("%.1f seconds", timeTaken) ..
                                 ", " .. Plural (numSteps, "knot") .. " shown"
  echoKP (message)
  EphemeralMessage (message)
end

function Stop ()
  executeKP ([[
    idle
    txt c 40 next "scenery delete;lua . GetNext ();lua . ShowIt ()"
  ]])
end

function View ()
  executeKP ([[
    txt centre
    txt fill on
    txt font 4
    txt c 40 stop "lua . Stop ()"
  ]])
  
  knotNumber = 1  -- note that variables in Lua are global by default
  DoUntil (ShowIt,  -- function that does something (takes and returns 0 arguments)
           GetNext, -- function that returns true when some task is completed
           999999,  -- time limit in seconds
           Finish)  -- function called upon task completing or if time limit is exceeded
end

--OpenSeq ("MCpolysL2M1span4run1num1.txt")
OpenSeq ("2x1-50.b")

leftMidpoints = {}
rightMidpoints = {}

left = -2
right = 2

v = Vector3
vs = Vector3.String


function equal (a, b)
  if math.abs (a - b) < 0.1 then
    return true
  end
  return false
end

function FindEnds ()
    
  leftMidpoints = {}
  rightMidpoints = {}

  vertex = getComponentKP (0)
  for i = 1, #vertex do
    x1 = vertex [i].x
    x2 = vertex [((i) % #vertex) + 1].x
    if equal (x1, x2) and equal (x1, left) then
      table.insert (leftMidpoints, Vector3.midpoint (vertex [i],
                                                     vertex [((i) % #vertex) + 1]))
    elseif equal (x1, x2) and equal (x1, right) then
            table.insert (rightMidpoints, Vector3.midpoint (vertex [i],
                                                     vertex [((i) % #vertex) + 1]))
    end
  end
end

function Mark ()
  FindEnds ()
  executeKP ("scenery delete")
  for i = 1, #leftMidpoints do
    executeKP (vs (leftMidpoints [i]), [[
      scenery object eobj/rsphere ARG1
    ]])
  end
  for i = 1, #rightMidpoints do
    executeKP (vs (rightMidpoints [i]), [[
      scenery object eobj/gsphere ARG1
    ]])
  end
  numberClosures = #leftMidpoints * #rightMidpoints
  SubTitle (Plural (numberClosures, "closure"))
  
  xpos = 15
  ypos = 55
  executeKP ([[
    txt delete group 108
    txt push
    txt group 108
    txt font 3
    txt left
    txt fill on
  ]])
  
  for i = 1, #leftMidpoints do
    for j = 1, #rightMidpoints do
      
      executeKP (xpos, ypos, i, j, [[
        txt ARG1 ARG2 "ARG3:ARG4" "lua . Cut (ARG3, ARG4)"
      ]])
      ypos = ypos + 30
    end
  end
  
  executeKP (ypos, [[
    txt fill off
    txt font 4
    txt 10 ARG1 "Cut:"
    txt pop
  ]])
end

function Cut (l, r)
  if l < 1 or r < 1 or l > #leftMidpoints or r > #rightMidpoints then
    echoKP ("bad values")
    return
  end
  executeKP (vs (leftMidpoints [l]), vs (rightMidpoints [r]), [[
    scenery delete
    load |last
    cut inside msphere 0.2 ARG1
    cut inside msphere 0.2 ARG2
  ]])
end

function Complain (complaint)
  echoKP (complaint)
  EphemeralMessage (complaint)
end

xoffset = v.new (0.5, 0, 0)
zoffset = v.new (0, 0, 3)

function CloseComponent (comp, up)
  local first = getComponentKP (comp, 1)
  local last = getComponentKP (comp, -1)
  if last [1].x < first [1].x then
    local swap = first
    first = last
    last = swap
  end
  local vf = v.sub
  if up then vf = v.add end
  p1 = v.sub (first [1], xoffset)
  p2 = vf (p1, zoffset)
  p4 = v.add (last [1], xoffset)
  p3 = vf (p4, zoffset)

  addComponentKP ({p1, p2, p3, p4})
end

function Close ()
  local info = mlcaptureKP ("info -full o")
  print ("info size is " .. #info)
  
  if #info ~= 2 then Complain ("must have two components") return end
  if info [1][1] ~= "o" or info [2][1] ~= "o" then Complain ("both components must be open") return end

  CloseComponent (0, true)
  CloseComponent (1, false)
  executeKP ("open all;join all")

end

function All ()
  executeKP ("")
end

function ID ()
  executeKP ("ago 33;align axes")
  kid = captureKP ("id")
  EphemeralMessage ("link type is " .. kid)
end

