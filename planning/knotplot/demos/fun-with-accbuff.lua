--[[

rob scharein
Tuesday, 23-Jan-24 01:24:30 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("fun-with-accbuff")

end   -- end of init block

--ButtonHelp ()



executeKP ('fun-with-accbuff.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
