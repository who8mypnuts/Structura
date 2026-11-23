--[[

10 July 2022, Rob Scharein

]]

require "Vector3"

executeKP ([[
  scenery vscale 0.8
  scenery dscale 1
  scenery rotate none
  scenery alpha 1
]])

labelHeight = 3
spacing = 1.02
deltaAngle = math.pi / 4

crossings = mlcaptureKP ("crossing")  -- returns a table of tables
for i = 1, #crossings do
  outputLine = crossings [i]
  angle = outputLine [9]
  label = outputLine [1] + 1
  x = outputLine [7]
  y = outputLine [8]
  crossingLoc = Vector3.new (x, y, labelHeight)
  offset = Vector3.new (math.cos (angle), math.sin (angle), 0)
  offset = Vector3.mult (offset, spacing)
  loc = Vector3.add (crossingLoc, offset)

  executeKP ("scenery object " .. label ..
    "-n " .. loc.x .. " " .. loc.y .. " " .. loc.z)
   
  if outputLine [10] == "1" then
    sign = "plus"
  else
    sign = "minus"
  end
  x = x + 1.02
  loc = Vector3.sub (crossingLoc, offset)
  executeKP ("scenery object " .. sign ..
    "-n " .. loc.x .. " " .. loc.y .. " " .. loc.z)

end
