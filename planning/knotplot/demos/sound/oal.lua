--[[

rob scharein
Thursday, 25-Jan-24 03:50:51 UTC

--]]

print (luaSource)

if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  Demo ()
  Title ("oal")

end   -- end of init block

ButtonHelp ()

executeKP ([[
  <sound/oal4.kps
]])





--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
