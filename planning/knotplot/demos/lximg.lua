convertLoc = "_not_set_"
rmLoc = "_not_set_"

dpi = 72

extraFlags = "-units PixelsPerInch -density " .. dpi

-- filename can contain spaces, but shouldn't contain any quotes
function LuxoImage (filename, numTiles, finalPixelSize)
  if convertLoc == "_not_set_" then
    echoKP ("have to set a value for `convertLoc'")
    return
  end
  if rmLoc == "_not_set_" then
    echoKP ("have to set a value for `rmLoc'")
    return
  end
  
  if filename == "/" then
    filename = captureKP ("save /?")
  end

  executeKP ("sbuff")
  ppmFile = "__tmp-" .. filename .. ".ppm"
  pngFile = filename .. ".png"
  executeKP ('imtile "' .. ppmFile .. '" ' .. numTiles)
  --echoKP ("creating `" .. pngFile .. "'")
  executeKP ("dbuff")
  convertCommand = convertLoc .. ' "' .. ppmFile .. '" -resize x' .. finalPixelSize .. " " .. extraFlags .. ' "' .. pngFile .. '"'
  --echoKP (convertCommand)
  os.execute (convertCommand)
  rmCommand = rmLoc .. ' "' .. ppmFile .. '"'
  --echoKP (rmCommand)
  os.execute (rmCommand)
  echoKP ("image written to `" .. pngFile .. "'")
end

  
