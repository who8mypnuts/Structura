--[[

rob scharein
Sunday, 04-Feb-24 17:09:11 UTC

some support routines for working with the knotted graphs
enumerated in the paper

A table of 0-curves and handcuff graphs with up to seven crossings
Hiromasa Moriuchi
Advanced Studies in Pure Mathematics 55, 2009 Noncommutativity and Singularities
pp. 281-290

--]]

-- the number of of a given crossing number
local numtheta = {}
numtheta [3] = 1
numtheta [4] = 1
numtheta [5] = 7
numtheta [6] = 16
numtheta [7] = 65

-- KnotPlot file names for the 0-curves in Table 1 of the paper
thetafile = {}
local thetaxing = {}
local thetaindex = {}

for k = 3, 7 do
  for j = 1, numtheta [k] do
    table.insert (thetafile, "t" .. k .. "." .. j)
    table.insert (thetaxing, k)
    table.insert (thetaindex, j)
  end
end

function thetaInfo (which)
  if which < 1 or which > #thetafile then
    echoKP ("bad index of " .. which .. " for theta curve")
    return
  end
  return thetaxing [which], thetaindex [which]
end
