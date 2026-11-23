--[[

rob scharein
Wednesday, 10-Jan-24 02:44:29 UTC

--]]

function ColourFromSet (colours)
  if RollDie == nil then
    echoKP ("needs RollDie() from Demo()")
    return
  end
  local set = explode (",", colours)
  for c = 0, paramKP ("ncomps") - 1 do
    executeKP (set [RollDie (#set)], c, [[
      echo colour ARG2 ARG1
      colour ARG2 ARG1
    ]])
  end
end




