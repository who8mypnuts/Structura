--[[

rob scharein
Tuesday, 23-Jan-24 00:16:48 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("toothpaste")

end   -- end of init block

--ButtonHelp ()



executeKP ('toothpaste.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
