--[[

rob scharein
Tuesday, 23-Jan-24 01:21:00 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("Dolphins")

end   -- end of init block

--ButtonHelp ()



executeKP ('Dolphins.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
