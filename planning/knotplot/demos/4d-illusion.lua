--[[

rob scharein
Tuesday, 23-Jan-24 00:15:04 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("4d-illusion")

end   -- end of init block

--ButtonHelp ()



executeKP ('4d-illusion.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
