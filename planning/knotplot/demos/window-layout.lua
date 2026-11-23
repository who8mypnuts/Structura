--[[

rob scharein
Sunday, 2024 August 18, 09:27:27 PDT

--]]

local file = 'test.kps'
if #arg == 1 then
  file = arg [1]
end

local output = '% ' .. captureKP ("date") .. '\n'
            .. '% using the command' .. '\n'
            .. '% lua do window-layout ' .. file .. '\n'

local function concat (t)
  local s = ""
  for j = 1, #t do
    s = s .. t [j] .. " "
  end
  return s
end

local screenInfo = mlcaptureKP ("screen")
for s = 1, #screenInfo do
  output = output .. '% ' .. concat (screenInfo [s]) .. '\n'
end

--[[

output from winfo looks like this:

Screen size = (1728, 1117).
view:  ID = 1, size = (827, 827), orig = (0, -827), min = (-1.00, -1.00), max = (1.00, 1.00).
cpanel:  ID = 2, size = (391, 760), orig = (1529, -999), min = (0.00, 0.00), max = (159.63, 307.69).
command:  ID = 3, size = (1092, 210), orig = (828, -210), min = (0.00, 0.00), max = (0.00, 0.00).

1         2  3 4  5    6 7      8     9      11    12

and should look like this:

resize command 1092 210 828 -210
resize cpanel 391 760 1529 -999
resize view 827 827 0 -827

--]]

local windowInfo = mlcaptureKP ("winfo")
for w = #windowInfo, 2, -1 do
  output = output .. 'resize'
          .. ' ' .. string.sub (windowInfo [w][1], 1, -2)
          .. ' ' .. string.sub (windowInfo [w][7], 2, -2)
          .. ' ' .. string.sub (windowInfo [w][8], 1, -3)
          .. ' ' .. string.sub (windowInfo [w][11], 2, -2)
          .. ' ' .. string.sub (windowInfo [w][12], 1, -3)
          .. '\n'
end

echoKP (output)


local fp = io.open (file, 'w')
echoKP ("saving to `" .. file .. "'")
io.output (fp)
io.write (output)
io.close (fp)

