--[[

rob scharein, 19 june 2023
in the Public Domain

--]]

if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    mode cb
    txt on
    txt clobber on
    show grid
    scenery on
    scenery dscale 0.3
    txt right
    txt font 3
    txt fill on
    txt lineskip -30
    txt -15 15 fullscreen "fullscreen toggle"
    txt -15 a  projection "lua . ToggleProjection ()"
    txt -15 a  grid "show ~grid"
    txt -15 a  axes "show ~axes"
    txt -15 a  turtle "lua . ToggleTurtleMode ()"
    txt fill off
    txt -10 a  toggle:
    txt fill on
    txt -15 a1.5 new "delete all; lua . turtleCommands ='';lua . Draw()"
    txt -15 a    delete "lua . DeleteLast ()"
    txt -15 a    safe  safe
    txt fill off
    txt -10 a action:
    
    txt push
    txt group 1
    txt font 4
    txt centre
    txt fill on
    txt fcolour black
    txt colour red
    txt c -70 "NOT SAFE"
    txt group 1 off
    txt pop
    
    txt push
    txt left
    txt fill off
    txt font 4
    txt lineskip 12
    txt 5 134 "keyboard:"
    txt 10 a2 "  e  "
    txt 10 a "             u"
    txt 10 a "a   s"
    txt 10 a "             j"
    txt 10 a "  z  "
    txt 5 a2.5 "spacebar to"
    txt 5 a2 "toggle turtle"
    
    txt pop
    
  ]])

  Demo ()
  
  projection = "perspective"

end   -- end of init block

keycodeTable = {  -- see https://www.lua.org/pil/3.6.html
  ["w"] = "n",    -- for information on contructing tables
  ["s"] = "e",
  ["a"] = "w",
  ["z"] = "s",
  ["u"] = "u",
  ["j"] = "d"
}

function Keyboard (x, y, keycode, down)
  -- this function should always return true!
  -- otherwise KnotPlot will get angry!!!
  
  if down then return true end
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
  SubTitle (projection .. " projection")
  if #turtleCommands < 1 then
    executeKP ([[
      scenery off
      txt group 1 off
      delete all
    ]])
    Title ("Create Knots & Links on the Simple Cubic Lattice")
    return
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
  
  executeKP ("jitter .01;save |x") -- need to do this to ensure general position
  if Safe () then
    executeKP ("txt group 1 off")
  else
    executeKP ("txt group 1 on")
  end
  executeKP ("load |x")

  
  local turtleLocation = lcaptureKP ("lsystem state")
  executeKP (turtleLocation [1], turtleLocation [2], turtleLocation [3], [[
    translate to 0 0 0   -- allow this location to be settable
    scenery delete
    scenery object eobj/wire-icosahedron ARG1 ARG2 ARG3
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
    txt c    80 ARG1 "lua . TurtleCommand ('ARG1')"   % N
    txt c+40 45 ARG2 "lua . TurtleCommand ('ARG2')"   % E
    txt c-40 45 ARG3 "lua . TurtleCommand ('ARG3')"   % W
    txt c    10 ARG4 "lua . TurtleCommand ('ARG4')"   % S
    txt c+90 65 ARG5 "lua . TurtleCommand ('ARG5')"   % U
    txt c+90 25 ARG6 "lua . TurtleCommand ('ARG6')"   % D
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
  
  Draw ()
end

CreateButtons ()
Draw ()

ShowSourceButton ()

--[[

stuff to do:

  allow the starting position to be settable


--]]
