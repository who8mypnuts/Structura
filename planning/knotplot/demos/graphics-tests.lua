--[[

rob scharein
Tuesday, 23-Jan-24 01:25:07 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("graphics-tests")

end   -- end of init block

--ButtonHelp ()



executeKP ('graphics-tests.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
