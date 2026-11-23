--[[

rob scharein
Tuesday, 23-Jan-24 01:21:49 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("bezier-drag")

end   -- end of init block

--ButtonHelp ()



executeKP ('bezier-drag.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
