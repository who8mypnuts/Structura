--[[

rob scharein
Tuesday, 23-Jan-24 00:22:40 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("SeaThings")

end   -- end of init block

--ButtonHelp ()



executeKP ('SeaThings.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
