--[[

rob scharein
Tuesday, 23-Jan-24 01:22:12 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("xsect")

end   -- end of init block

--ButtonHelp ()



executeKP ('xsect.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
