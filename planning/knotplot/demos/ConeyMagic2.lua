--[[

rob scharein
Tuesday, 23-Jan-24 01:19:55 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("ConeyMagic2")

end   -- end of init block

--ButtonHelp ()



executeKP ('ConeyMagic2.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
