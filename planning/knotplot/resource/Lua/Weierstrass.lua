--[[

rob scharein
Tuesday, 13-Feb-24 23:50:10 UTC

The Weierstrass P function, evaluated at omega1=4 omega2=0
  
--]]

#require "complex"

function WeierstrassP (z)
  local s = complex.new (0, 0)
  local z2 = complex.mult (z, z)
  local z4 = complex.mult (z2, z2)
  local z6 = complex.mult (z4, z2)
  local z8 = complex.mult (z6, z2)

  
end

