--[[

rob scharein, 22 june 2023

--]]

if convertPath == "not set" then
  executeKP ([[
    echo add a line of the form
    echo lximgout -path /path/to/convert
    echo in the same place you put your key (preferences... button on panel Main)
    echo and then restart KnotPlot (you only have to do this once)
  ]])
else
  local luxoDebug = true
  
  if luxoDebug then
    print ("convert " .. convertPath)
    print ('file ' .. luxoFilename)
    print ('tiles ' .. luxoNumTiles)
    print ('height ' .. luxoImageHeight)
  end
  
  local dpi = 72
  local extraFlags = "-units PixelsPerInch -density " .. dpi

  if luxoFilename == "/.png" then
    luxoFilename = captureKP ("save /?") .. ".png"
  end

  executeKP ("sbuff")
  local ppmFile = captureKP ("tempfile") .. ".ppm"
  executeKP ('imtile "' .. ppmFile .. '" ' .. luxoNumTiles)
  executeKP ("dbuff")
  local convertCommand = '"' .. convertPath .. '" "' .. ppmFile .. '" -resize x' .. luxoImageHeight .. " " .. extraFlags .. ' "' .. luxoFilename .. '"'
  if luxoDebug then
    print (convertCommand)
  end
  os.execute (convertCommand)
  echoKP ("image written to `" .. luxoFilename .. "' with height " .. luxoImageHeight)
  os.remove (ppmFile)
end



