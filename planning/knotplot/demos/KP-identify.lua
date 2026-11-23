require "KP-ktools"

if jhomfly ~= nil and jidknot ~= nil then
  local egc = captureKP ("gauss")
  local com = 'echo "' .. egc .. '" | "' .. jhomfly .. '" -- | "' .. jidknot .. '" -- -k'
  --if verbose then print (com) end
  local knotID = osx (com)
  --if verbose then print (knotID) end
  echoKP (knotID)
else
  echoKP ("one or both of the knotting tools are missing")
end





