--[[

rob scharein
Tuesday, 23-Jan-24 00:16:35 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("field_lorenz")

end   -- end of init block

--ButtonHelp ()



executeKP ('field_lorenz.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
