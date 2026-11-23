--[[

rob scharein, 17 june 2023

--]]

if eps2pdfConverter == "not set" then
  executeKP ([[
    echo add a line of the form
    echo pdfout -path /path/to/theconverter
    echo in the same place you put your key (preferences... button on panel Main)
    echo and then restart KnotPlot (you only have to do this once)
  ]])
else
  --echoKP ("using " .. eps2pdfConverter)
  --echoKP ("and " .. eps2pdfFilename)
  local tempEPSfile = captureKP ("tempfile") .. ".eps"
  local com = "psout " .. tempEPSfile
  --print (com)
  executeKP (com)
  
  com = '"' .. eps2pdfConverter .. '"' .. ' "' .. tempEPSfile .. '" "'
       .. eps2pdfFilename .. '"'
  --print (com)
  os.execute (com)
  os.remove (tempEPSfile)
  --print ("done!")
end



