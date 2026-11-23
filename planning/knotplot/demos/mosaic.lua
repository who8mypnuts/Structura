--[[

rob scharein, 2 december 2023
modified 26 january 2024

can be called from the command line in KnotPlot, as in
  lua do mosaic 021000 2x7100 37x710 039x91 003984 000340
which creates a 6.3 knot

also, can be called from Lua.  from the KnotPlot in your Lua script
do the following:
  lua do mosaic init
you only need to do this once.  after you do this, the MakeMosaic()
function is defined.  this function takes a table of strings, as in
  MakeMosaic ({'021000', '2x7100', '37x710', '039x91', '003984', '000340'}
which does the same thing as the example above.

see the demo mosaics.lua that uses this init technique, try entering
  lua . example ()
from KnotPlot after you run mosaics.lua


--]]

function MakeMosaic (word)  -- table of strings
  local kount = 0
  executeKP ("parsave;verbose = 0")
  
  for row = 1, #word do
    local r = word [row]
    for col = 1, #r do
      local n = string.sub (r, col, col)
      if n == "t" or n == "x" then n = 10 end
      local tilefile = "mosaic-t" .. n
      executeKP (tilefile, col * 20, row * -20, kount, [[
        load ARG1
        translate ARG2 ARG3 0
        save |ARG4
      ]])
      kount = kount + 1
    end
  end
  
  executeKP ("delete all")
  for i = 0, kount - 1 do
    executeKP (i, [[
      load combine |ARG1
    ]])
  end
  executeKP ([[
    reap 4
    jthresh = 7
    join all
    centre
    scale 0.4
    parrestore
  ]])
end

if #arg == 0 then
  executeKP ([[
    echo need some arguments, for example:
    echo lua do mosaic 21 34
    echo creates an unknot and
    echo lua do mosaic 021000 2x7100 37x710 039x91 003984 000340
    echo creates a 6.3 knot
  ]])
  return
end

if arg [1] == "init" then   -- used when we just want to define the MakeMosaic function
  return
end

MakeMosaic (arg)


