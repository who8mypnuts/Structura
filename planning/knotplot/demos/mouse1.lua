Demo ()
RequireKLE (7)


require "Vector3"
lastPos = Vector3.new (999, 999, 999)

function WindowToWorld (winx, winy, winz)
  local com = "vpunproject " .. winx .. " " .. winy .. " " .. winz
  local s = lcaptureKP (com)
  return s [1], s [2], s [3]
end

function CreateSphere (x, y, z, colour)
  local pos = Vector3.new (x, y, z)
  if Vector3.distance (pos, lastPos) < 1.02 then return end
  executeKP (pos.x, pos.y, pos.z, colour, [[
    scenery object eobj/ARG4sphere.eobj ARG1 ARG2 ARG3
  ]])
  lastPos = pos
end

rc = true

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

function Pokey (winx, winy)
  local txt = "move to " .. winx .. ", " .. winy
  executeKP (txt, 'txt c -20 "ARG1"')
  worldx, worldy, worldz = WindowToWorld (winx, winy, winz)
  CreateSphere (worldx, worldy, worldz, "w")
  return rc
end

function Minga (winx, winy)
  local txt = "passive move to " .. winx .. ", " .. winy
  executeKP (txt, 'txt c 20 "ARG1"')
  worldx, worldy, worldz = WindowToWorld (winx, winy, winz)
  CreateSphere (worldx, worldy, worldz, "y")
  return rc
end

executeKP ([[
  reset all
  txt on
  txt clobber on
  txt centre
  txt font 4
  show grid
  scenery on
  scenery dscale 0.14
  txt fill on
  txt 50 20 toggle "lua . rc = not rc echoKP ('rc is ' .. tostring (rc))"
  txt fill off
]])

SetMouseFunc (Gumby)
SetMouseMotionFunc (Pokey)
SetMousePassiveMotionFunc (Minga)

origin = lcaptureKP ("vpproject 0 0 0")
winz = origin [3]
echoKP (tostring (winz))
