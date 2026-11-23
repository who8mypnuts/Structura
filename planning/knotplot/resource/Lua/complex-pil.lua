--[[

rob scharein
Tuesday, 13-Feb-24 22:39:50 UTC

From Programming in Lua, section 15.1
https://www.lua.org/pil/15.1.html

for a more complete implementation of complex numbers
using Lua metatables see complex.lua in this directory

--]]

complex = {}
    
function complex.new (r, i) return {r=r, i=i} end

-- defines a constant `i'
complex.i = complex.new (0, 1)

function complex.add (c1, c2)
  return complex.new (c1.r + c2.r, c1.i + c2.i)
end

function complex.sub (c1, c2)
  return complex.new (c1.r - c2.r, c1.i - c2.i)
end

function complex.mul (c1, c2)
return complex.new (c1.r * c2.r - c1.i * c2.i,
  c1.r * c2.i + c1.i * c2.r)
end

function complex.inv (c)
  local n = c.r^2 + c.i^2
  return complex.new (c.r / n, -c.i / n)
end

return complex
