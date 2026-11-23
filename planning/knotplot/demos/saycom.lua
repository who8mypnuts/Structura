--[[

rob scharein
Monday, 26-Feb-24 16:09:55 UTC

say the result of a command

lua do saycom info
lua do saycom timer check

--]]

local function SayCommand ()
  local com = ""
  for i = 1, #arg do
    com = com .. " " .. arg [i]
  end

  echoKP (com)
  local what = mlcaptureKP (com)
  if what == nil then
    -- no output
    return
  end
  if what [1][1] == "***" then
    -- unknown command
    return
  end
  
  
  
  local stuff = ""
  for i = 1, #what [1] do
    stuff = stuff .. " " .. what [1][i]
  end

  executeKP (stuff, [[
    echo ARG1
    echo -f
    say ARG1
  ]])
  
end

print ("#arg is " .. #arg)
if #arg == 0 then
  echoKP ("lua do saycom COMMAND")
else
  SayCommand ()
end


