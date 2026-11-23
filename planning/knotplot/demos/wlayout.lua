--[[

rob scharein, 11 july 2023

--]]

  local screen = captureKP ("screen main")
  if screen == "1728x1117" then
    executeKP ([[
      play 88
      resize command 678 262 1050 855
      resize cpanel 391 760 1052 66
      resize view 1051 1051 0 66
    ]])
  elseif screen == "16x9" then
    executeKP ([[
      play 60
      resize command 867 225 1014 843
      resize cpanel 391 760 1014 53
      resize view 1011 1011 2 53
    ]])
  else
    executeKP ([[
      play 32
    ]])
  end
 
