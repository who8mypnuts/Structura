--[[

rob scharein
Monday, 22-Jan-24 23:49:30 UTC

--]]

which = arg [1]   -- Demo () resets arg, so use now

if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  Demo ()

end   -- end of init block

executeKP (which, [[
  echo running KnotPaintARG1.kps
  <KnotPaintARG1.kps
]])




--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
