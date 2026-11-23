--[[

rob scharein
Friday, 2024 August 23, 11:10:03 PDT

--]]


if #arg == 2 then
  executeKP (chooseKP (arg [1], arg [2]))
elseif #arg == 1 then
  local probs = ""
  local spacer = ""
  local expl = explode (",", arg [1])
  for i = 1, #expl do
    probs = probs .. spacer .. '1'
    spacer = ','
  end
  executeKP (chooseKP (arg [1], probs))
else
  echoKP ([[
usage:
  lua do chooseone "COMMAND1,COMMAND2"  "PROB1,PROB2"
]])
end
