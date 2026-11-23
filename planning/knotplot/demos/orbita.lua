--[[

rob scharein
Monday, 22-Jan-24 23:38:38 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    <orbita.kps
  ]])

  Demo ()

end   -- end of init block






--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
