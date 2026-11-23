--[[

rob scharein
Monday, 22-Jan-24 23:49:30 UTC

--]]

whichSnake = tonumber (arg [1])   -- Demo () resets arg, so use now

if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  Demo ()

end   -- end of init block

local snakes = {"20oct05a", "31jan14", "dropA"}

executeKP (snakes [whichSnake], [[
  echo running ARG1.kps
  <ARG1.kps
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
