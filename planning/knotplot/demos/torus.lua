--[[

A example of how to create a knot or link programmatically in Lua.
Of course, torus knots have been part of KnotPlot for decades.
You can use the button on the bottom of the window to compare
the Lua construction to the KnotPlot one.  They should be identical.

rob scharein, 1 April 2022

--]]

require "Vector3"

if demo ~= luaSource then
  Demo ()
  demo = luaSource
  executeKP ("reset all")
  ShowSourceButton ()
end

if FlipCoin () then
  executeKP ("mode cb;cyl-rad = 0.12")
else
  executeKP ("mode s;cyl-rad = 0.2")
end

executeKP ([[
  delete all
  txt clobber on
]])

-- create an (n, m) torus link and send it to KnotPlot

function randInt (min, max)
  return Random ("ri[" .. min .. "/" .. max .. "]")
end

function gcd (a, b)     -- greatest common divisor
  if (b == 0) then
    return a
  else
    return gcd (b, a % b)
  end
end

n = randInt (1, 10)
m = randInt (n, 2 * n + 6)

if Random ("rr100") < 20 then
  swap = n
  n = m
  m = swap
end

Ncomp = gcd (n, m)
Krequested = randInt (77, 222)
R = Random ("rr[8/11]")
d = Random ("rr[1.4/4.4]")    

beads_per_component = math.floor (Krequested / Ncomp)
K = beads_per_component * Ncomp
if Ncomp > 1 then
  kind = "link"
else
  kind = "knot"
end

Title (n .. ", " .. m .. " torus " .. kind)
BotButton ("compare to constructing it in KnotPlot",
           "torus " .. n .. " " .. m .. " " .. Krequested .. " " .. R .. " " .. d)

tinc = 2.0 * math.pi / K

t = 0.0

extraIncr = 2.0 * math.pi / math.floor (m / Ncomp) / Ncomp;
extra = 0.0

for comp = 1, Ncomp do
  component = {}        -- create an empty table

  for i = 1, beads_per_component do
    theta = t * n
    r = R + d * math.cos (t * m)
    z = d * math.sin (t * m)
    table.insert (component,
                  Point.new (r * math.cos (theta + extra), r * math.sin (theta + extra), z))
    t = t + tinc
  end

  addComponentKP (component)
  
  extra = extra + extraIncr
end


executeKP ("hincr = " .. 360.0 / Ncomp)
executeKP ("info;safe")



