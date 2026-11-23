--[[

rob scharein
Sunday, 2024 August 18, 13:54:52 PDT

--]]


if #arg >= 2 then
  local commands = ''
  local probs = ''
  local spacer = ''
  for i = 1, #arg do
    commands = commands .. spacer .. arg [i]
    probs = probs .. spacer .. '1'  -- all probabilities are the same
    spacer = '|'
  end
  executeKP (chooseKP (commands, probs, spacer))
else
  echoKP ("usage:\n  lua do pickone COMMAND1 COMMAND2 ...")
  echoKP ("  as in:")
  echoKP ('  lua do pickone "load 4.1" "load 6.3"')
  echoKP ('  lua do pickone "torus 3 2" "chain 9" "braid (A^2Bc^2)^2"')
  echoKP ("randomly chooses one of a bunch of commands and executes it")
  echoKP ("for more interesting examples using chooseKP(), look in chooseKP.lua")
end

