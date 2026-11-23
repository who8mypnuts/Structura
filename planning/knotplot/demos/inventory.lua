function Inventory (smallLarge)
  if paramKP ("nbeads") == 0 then return 0,0 end
  local kountSmall = 0
  local kountLarge = 0
  local info = mlcaptureKP ("info -full b")
  for i = 1, #info do
    if tonumber (info [i][1]) > smallLarge then
      kountLarge = kountLarge + 1
    else
      kountSmall = kountSmall + 1
    end
  end
  return kountSmall, kountLarge
end

