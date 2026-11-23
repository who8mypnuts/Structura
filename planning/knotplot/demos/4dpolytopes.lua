--[[

rob scharein
Tuesday, 23-Jan-24 00:14:34 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("4dpolytopes")

end   -- end of init block

--ButtonHelp ()



executeKP ('4dpolytopes.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
