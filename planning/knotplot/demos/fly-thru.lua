--[[

rob scharein
Tuesday, 23-Jan-24 01:23:59 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("fly-thru")

end   -- end of init block

--ButtonHelp ()



executeKP ('fly-thru.kps', [[
  <ARG1
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
