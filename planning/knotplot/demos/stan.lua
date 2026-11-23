--[[

rob scharein
Tuesday, 23-Jan-24 01:22:41 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  --Demo ()
  --Title ("stan")

end   -- end of init block

--ButtonHelp ()



executeKP ('stan.kps', [[
  <ARG1
  tfunc 1 "txt click 2"
]])


