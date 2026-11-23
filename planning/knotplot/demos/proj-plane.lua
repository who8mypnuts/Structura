--[[

rob scharein
Tuesday, 23-Jan-24 00:15:25 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("proj-plane")

end   -- end of init block

--ButtonHelp ()



executeKP ('proj-plane.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
