--[[

rob scharein, 26 november 2023

--]]

local function ShowHelp ()
  if luaSource == nil then
    echoKP ("luaSource not set")
    return
  end
  
  
  --print ("luaSource is " .. luaSource)
  
  executeKP (luaSource, [[
  
    %echo help popup ARG1 handoff
    help popup ARG1 handoff

  ]])

end

ShowHelp ()



