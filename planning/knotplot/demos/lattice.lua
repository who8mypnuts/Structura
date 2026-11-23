--[[

rob scharein, 13 december 2023
modified from NEWSUD.lua
in the Public Domain

arm 890ba041076f5b396373f7f20ece1f97  CET
x64 a1985a5b3678ae27c56551cf01f77791  AST


--]]


fullversion = false

if demo ~= luaSource .. #arg then
  demo = luaSource .. #arg
  --print (demo)
  executeKP ([[
    reset all

    mode cb
    txt on
    txt clobber on
    scenery on
    scenery dscale 1
    
    alias todo "lua . ToDo()"
    
    txt push
    txt group 1
    txt font 4
    txt centre
    txt fill on
    txt fcolour black
    txt scolour #000
    txt sfcolour #fb0 .8

    txt colour red
    txt c -70 "NOT SAFE"
    txt group 1 off
    txt pop
    
    function 2 "www en.wikipedia.org/wiki/L-system"
    
    txt push
    txt left
    txt fill off
    txt font 4
    txt lineskip 12
    txt 5 134 "keyboard:"
    txt 10 a2 "  w  "
    txt 10 a "             u"
    txt 10 a "a   s"
    txt 120 a0 "[  ]"
    txt 10 a "             j"
    txt 10 a "  z  "
    txt 5 a2.5 "spacebar to"
    txt 5 a2 "toggle draw/move"
  
    %noclobber = true
    
    txt pop
    
    alias demob "lua . DemoB()"
    
    show axes grid
    
  ]])

  Demo ()
      
  require "Lsystem"
  require "Primitives"

  Title ("Create Knots / Links & Graphs on the Simple Cubic Lattice")
  projection = "perspective"
  
  firstcall = true
    
  ButtonHelp ()
  
  tgm = ""
  if fullversion then tgm = "draw mode,lua . ToggleDrawingMode()," end
  
  ButtonStack ("toggle:,axes,show ~axes,grid,show ~grid,labels,show ~labels," .. tgm .. "projection,lua . ToggleProjection(),turtle mode,lua . ToggleTurtleMode(),fullscreen,fullscreen toggle")
  
  if fullversion then
    ButtonStack ("action:,refl x,refl x,refl y,refl y,refl z,refl z,fitto 10,fitto 10,embed clk,embed clk,delete 1,delete 1,open,open all;close 0,to do,todo,untran,untran")
  else
    ButtonStack ('action:,safe,lua . CheckSafe(),delete,lua . DeleteLast(),new,lua . New()')
  end
  
  ButtonStack ("select on,group 222|create:,knots,lua . Create(1),graphs,lua . Create(0)")
  
  if not fullversion then
    ButtonStack ("rotate:,x up,lua . RotateAxisUp(1),y up,lua . RotateAxisUp(2),z up,lua . RotateAxisUp(3)")
  end
  
  ButtonStack ("extra:,backdrop,lua . backdrop()")
  
  
end   -- end of init block

keycodeTable = {  -- see https://www.lua.org/pil/3.6.html
  ["w"] = "n",    -- for information on constructing tables
  ["s"] = "e",
  ["a"] = "w",
  ["z"] = "s",
  ["u"] = "u",
  ["j"] = "d",
  ["["] = "[",
  ["]"] = "]"
}

function New ()
  turtleCommands = ''
  Draw ()
end

creatingKnots = true  

function Create (ck)
  creatingKnots = ck == 1
  local m = "creating "
  if creatingKnots then
    m = m .. "knots and links"
  else
    m = m .. "knotted graphs"
  end
  EphemeralMessage (m)
  Draw ()
end

startbead = 0
endbead = 0

function MakeJoin ()
  local startloc = captureKP ("bead " .. startbead)
  local endloc = captureKP ("bead " .. endbead)
  executeKP (startloc, endloc, [[

    lattice path ARG1 ARG2 > x
    load combine x

    open 1
  ]])
end

function Keyboard (x, y, keycode, down)
  -- this function should always return true!
  -- otherwise KnotPlot will get angry!!!
  
  if down then return true end
  if keycode == "`" then
    executeKP ("test drag on")
    return
  elseif keycode == "1" then
    startbead = captureKP ("mouse bead")
    echoKP ("start bead set to " .. startbead)
    return
  elseif keycode == "2" then
    endbead = captureKP ("mouse bead")
    echoKP ("end bead set to " .. endbead)
    return
  elseif keycode == "3" then
    MakeJoin ()
    return
  end
  
  if keycode == " " then ToggleTurtleMode () return true end
  local c = keycodeTable [keycode]
  if c == nil then return true end
  
  if charAt (newsud, 1) == 'N' then
    c = string.upper (c)
  end
  TurtleCommand (c)
  
  return true
end

SetKeyboardFunc (Keyboard)

function ToggleTurtleMode ()
  if charAt (newsud, 1) == 'N' then
    newsud = string.lower (newsud)
  else
    newsud = string.upper (newsud)
  end
  CreateButtons ()
end

newsud = "NEWSUD"
turtleCommands = ""

function TurtleCommand (com)
  turtleCommands = turtleCommands .. com
  Draw ()
end

function DeleteLast ()
  if #turtleCommands < 2 then
    turtleCommands = ""
  else
    turtleCommands = string.sub (turtleCommands, 1, -2)
  end
  Draw ()
end

function Draw ()
  local m = projection .. " projection, "
  if creatingKnots then m = m .. "knot / link" else m = m .. "graph" end
  SubTitle (m .. " mode")
  if #turtleCommands < 1 then
    executeKP ([[
      scenery off
      txt group 1 off
      delete all
    ]])
    Title ("Create Knots & Links on the Simple Cubic Lattice")
    
    return
  end
  
  function CheckSafe ()
    if not creatingKnots then
      EphemeralMessage ("in graph mode, ignoring request")
      return
    end
    if Safe () then
      EphemeralMessage ("current position is safe")
    else
      EphemeralMessage ("current position is not safe")
    end
    executeKP ("safe")
  end
  
  executeKP (turtleCommands, [[
    echo
    scenery on
    lsystem init
    lsystem axiom ARG1
    lsystem 0
  ]])

  local produce = captureKP ("lsystem produce")
  if #produce < 55 then
    Title (produce)
  else
    Title ("...")
  end
  
  if paramKP ("ncomps") ~= 0 and creatingKnots then
    executeKP ("jitter .01;save |x") -- need to do this to ensure general position
    if Safe () then
      executeKP ("txt group 1 off")
    else
      executeKP ("txt group 1 on")
    end
    executeKP ("load |x")
  end

  
  local turtleLocation = lcaptureKP ("lsystem state")
  executeKP (turtleLocation [1], turtleLocation [2], turtleLocation [3], [[
    translate to 0 0 0   -- allow this location to be settable
    scenery delete group 1
    scenery group 1
    scenery push
    scenery vscale 0.3
    scenery object eobj/wire-icosahedron ARG1 ARG2 ARG3
    scenery pop
    display true
  ]])
end

function CreateButtons ()
  executeKP (charAt (newsud, 1),
             charAt (newsud, 2),
             charAt (newsud, 3),
             charAt (newsud, 4),
             charAt (newsud, 5),
             charAt (newsud, 6),
  [[
    txt fill on
    txt font 4
    txt centre
    txt c     80 ARG1 "lua . TurtleCommand ('ARG1')"   % N
    txt c+40  45 ARG2 "lua . TurtleCommand ('ARG2')"   % E
    txt c-40  45 ARG3 "lua . TurtleCommand ('ARG3')"   % W
    txt c     10 ARG4 "lua . TurtleCommand ('ARG4')"   % S
    txt c+90  65 ARG5 "lua . TurtleCommand ('ARG5')"   % U
    txt c+90  25 ARG6 "lua . TurtleCommand ('ARG6')"   % D
    txt c+140 45 "["  "lua . TurtleCommand ('[')"      % [ FIFO stack push
    txt c+190 45 "]"  "lua . TurtleCommand (']')"      % ] FIFO stack pop
   ]])
end

function backdrop ()
  if not FileExists ("backdrop.png") then return end
  
  executeKP ([[
    scenery on
    scenery delete group 2
    scenery group 2
    scenery rotate billboard
    scenery object lpoly-n 0 0 0
  ]])

end

function ToggleProjection ()
  if projection == "perspective" then
    projection = "orthographic"
    executeKP ("ortho")
  else
    projection = "perspective"
    executeKP ("persp")
  end
end

CreateButtons ()

ShowSourceButton ()


function Minga (winx, winy)
  local txt = "passive move to " .. winx .. ", " .. winy
  --print (txt)
  local bnum = captureKP ("mouse bead " .. winx .. " " .. winy)
  echoKP (bnum)
  return true
end


function Gumby (winx, winy, b, upDown)
  local txt = "down"
  if upDown then txt = "up" end
  txt = txt .. " at " .. winx .. ", " .. winy
  worldx, worldy, worldz = WindowToWorld (winx, winy, winz)

  executeKP (txt, 'txt c -20 "ARG1"')

  if upDown then
    lastPos = Vector3.new (999, 999, 999)
    CreateSphere (worldx, worldy, worldz, "r")
  else
    lastPos = Vector3.new (999, 999, 999)
    CreateSphere (worldx, worldy, worldz, "g")
  end
  return rc
end


--SetMousePassiveMotionFunc (Minga)
--SetMouseFunc (Gumby)

numtheta = {}
numtheta [3] = 1
numtheta [4] = 1
numtheta [5] = 7
numtheta [6] = 16
numtheta [7] = 65

function ToDo ()
  local todo = ""
  echoKP (todo)
  for k = 3, 7 do
    for j = 1, numtheta [k] do
      local fname = "t" .. k .. "." .. j
      if not FileExists (fname) then
        todo = todo .. fname .. " "
        --kount = kount + 1
        --if kount % 10 == 0 then todo = todo .. "\n" end
        if #todo > 60 then
          echoKP (todo)
          todo = ""
        end
      end
    end
  end
  echoKP (todo)
end

function DemoB ()
  osx ("demo-k.php t3.1 t4.1 t5.? t6.? t6.?? t7.? t7.??")
end

function ToggleDrawingMode ()
  if captureKP ("mode") == "mode s" then
    executeKP ("mode cb")
  else
    executeKP ("mode s")
  end
end

if firstcall then
  executeKP ([[
    txt click knots
  ]])
  firstcall = false
end

--[[

stuff to do:

  allow the starting position to be settable

BEGIN HELP

Things to do:

  Draw a new knot or graph by clicking on the buttons on the bottom of the screen.
  If you are a computer gamer, you may be familiar with moving by using the keyboard.
  Use the keys w a s z to draw N W E S or move n w e s. This is an alternative to
  using the buttons.
  
  Switch between creating edges with N E W S U and D to moving the turtle with
  n e w s u and d by toggling the turtle mode.
  
  Use the [ and ] buttons or the corresponding keys to push and pop the turtle state.

  create:
    Switch between creating knots or creating graphs.  The only difference is that KnotPlot
    won't complain about being in an `unsafe' position whilst in graph mode.
    
  rotate:
    Convenience methods to rotate the chosen axis to being exactly vertical. This may be
    useful when you are exporting knot diagrams.
    
  action:
    delete - deletes last edge added
    new - starts a new knot
    safe - checks for safeness
    

This demo uses KnotPlot's built-in L-system generator. The NEWSUD string is set as the "axiom"
and the number of production steps is 0. There are no rules.

Try running the lsystems demo to see what L-systems can do.
  
https://en.wikipedia.org/wiki/L-system
(press F2 to go to this web page now)



END HELP

--]]
