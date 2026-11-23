--[[

rob scharein
Saturday, 2024 September 7, 09:39:24 PDT

--]]

function drawCallback (where,  -- ignore this
                       comp)   -- component being drawn
  comp = tonumber (comp)

  local colour = 'black'
  if oa_table.colour [comp] ~= nil then
    colour = oa_table.colour [comp]
  end
  
  local scale = 1
  if oa_table.scale [comp] ~= nil then
    scale = oa_table.scale [comp]
  end
  
  executeKP (colour, scale, [[
    set colo ARG1
    set oscale ARG2
  ]])
end

local function init ()
  oa_table = {}
  oa_table.colour = {}
  oa_table.scale = {}
  print (captureKP ("date"))
  executeKP ([[
    verbose = 2
    lua draw drawCallback
    verbose = 1
  ]])
end


if oa_table == nil then
  init ()
end

if #arg == 1 and arg [1] == 'init' then
  init ()
elseif #arg == 3 then
  local comp = tonumber (arg [2])
  if arg [1] == 'colour' then
    oa_table.colour [comp] = arg [3]
  elseif arg [1] == 'scale' then
    oa_table.scale [comp] = arg [3]
  else
    echoKP ("unknown option `" .. arg [2] .. "'")
  end
  executeKP ("display true")
else
  echoKP ([[
Usage:
  lua do oa init
  lua do oa scale COMPONENT SCALE
  lua do oa colour COMPONENT COLOUR
]])
end

-- change `true' to `false' below if you
-- don't want the convenient aliases defined

if true then
  executeKP ([[
    alias oac "lua do oa colour $0 $1"
    alias oas "lua do oa scale  $0 $1"
  ]])
end

