Demo ()
RequireKLE (7)


require "Primitives"


function WindowToWorld (winx, winy, winz)
  local com = "vpunproject " .. winx .. " " .. winy .. " " .. winz
  local s = lcaptureKP (com)
  return s [1], s [2], s [3]
end

function Minga (winx, winy)
  local txt = "passive move to " .. winx .. ", " .. winy

  worldx, worldy, worldz = WindowToWorld (winx, winy, winz)
  top = Vector3.new (worldx, worldy, worldz + 5)
  bot = Vector3.new (worldx, worldy, worldz - 5)
  
  --Cylinder (top, bot, 1.02, 12, "orange")
  --CreateSphere (worldx, worldy, worldz, "y")
  
  executeKP (worldx, worldy, worldz, "o", [[
    scenery delete
    scenery object eobj/wire-icosahedron.eobj ARG1 ARG2 ARG3
  ]])

  return true
end

executeKP ([[

  scenery on
  scenery dscale 5
  
]])


SetMousePassiveMotionFunc (Minga)

origin = lcaptureKP ("vpproject 0 0 0")
winz = origin [3]
