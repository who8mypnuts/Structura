-- 27 September 2022, Rob Scharein
-- in the Public Domain

--       number of crossings: 0  1  2  3  4  5  6  7   8   9   10
local number_prime_knots =   {1, 0, 0, 1, 1, 2, 3, 7, 21, 49, 165, -- 1 component
                              1, 0, 1, 0, 1, 1, 3, 8, 16, 61,   0, -- 2 components
                              1, 0, 0, 0, 0, 0, 3, 1, 10, 21,   0, -- 3 components
                              1, 0, 0, 0, 0, 0, 0, 0,  3,  1,   0, -- 4 components
                              1, 0, 0, 0, 0, 0, 0, 0,  0,  0,   0} -- 5 components
Utilities = {}
                      
function Utilities.RolfsenName (N)  -- unfinished function, should probably be in KnotTheory package
  local ncross = 0
  local index = 0
  local number = index
  local ncomp = 1
end

function Utilities.writeMETA (filename,  -- write to this file
                              metas)     -- a table of meta key / value pairs or
                                         -- ommitted in which case the current
                                         -- metas are read
  local metas = lcaptureKP ("meta")
  if #metas == 0 then
    echoKP ("no meta")
    return nil
  end
  
  return metas
end

function Utilities.meta ()
  --[[
  
  return the metas of the currently loaded knot as a table
  usually, the metas have a single word as the key and possibly
  more than one word as the value, as in
  Creator: orb
  Hostname: Athena
  symmetry: D2
  CreationDate: 2023-05-10 03h17m02s UTC
  but the keys could have multiple words as well, as in
  knot family: twist
  the first word that ends in a : is considered to be the end of the key
  
  run
  lua do test/meta
  to test this utility

  rgs - 19 august 2024
  
  --]]
  
  local metas = mlcaptureKP ("meta")  -- returns a table of tables
  if metas == nil then return nil end
  local metaTable = {}   -- a table of KnotPlot knot meta values
  for m = 1, #metas do   -- not to be confused with a `metatable' in Lua
    local str = ''
    local space = ''
    
    for i = 1, #metas [m] do
      str = str .. space .. metas [m][i]
      space = ' '
    end
    
    local exp = explode (": ", str)
    -- should probably return nil if #exp ~= 2
    metaTable [exp [1]] = exp [2]
  end
  return metaTable
end
