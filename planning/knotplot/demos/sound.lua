--[[

rob scharein
Thursday, 25-Jan-24 04:01:55 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  Demo ()
  Title ("sound")

end   -- end of init block

ButtonHelp ()

executeKP ([[
  <sound/init.kps
]])



--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
