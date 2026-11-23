--[[

rob scharein
Tuesday, 23-Jan-24 01:24:15 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("cyclization")

end   -- end of init block

--ButtonHelp ()



executeKP ('cyclization.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
