--[[

rob scharein
Tuesday, 23-Jan-24 00:20:48 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("UnknotFlowers")

end   -- end of init block

--ButtonHelp ()



executeKP ('UnknotFlowers.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
