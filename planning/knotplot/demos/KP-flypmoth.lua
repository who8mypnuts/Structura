require "KP-ktools"

if jhomfly ~= nil then
  local egc = captureKP ("gauss")
  local com = 'echo "' .. egc .. '" | "' .. jhomfly .. '" -- '
  local poly = osx (com)
  echoKP (poly)
else
  echoKP ("one of the knotting tools is missing")
end



