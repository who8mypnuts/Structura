--[[

rob scharein
Tuesday, 23-Jan-24 01:36:57 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("collide")
  
  

end   -- end of init block

--ButtonHelp ()


executeKP (arg [1], [[
  echo running collideARG1.kps
  <collideARG1.kps
]])


--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
