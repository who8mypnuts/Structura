function Demo ()
  -- calling Demo () will reset the arg global variable
  -- if you use Demo () make sure you save any values you might
  -- need from the arguments passed to your script
  executeKP ("lua do Demos-init.lua")
end

-- https://stackoverflow.com/questions/132397/get-back-the-output-of-os-execute-in-lua

function osx (cmd)  -- execute a command line and return its output
  local f = assert (io.popen (cmd, 'r'))
  local s = assert (f:read('*a'))
  f:close ()
  s = string.gsub(s, '[\n\r]+', '')
  return s
end

function FileExists (fileName)
   local f = io.open (fileName, "r")
   if f ~= nil then io.close (f) return true else return false end
end


function explode (div, str) -- credit: http://richard.warburton.it
                            --    via: http://lua-users.org/wiki/MakingLuaLikePhp
  if (div == '') then return false end
  local pos, arr = 0, {}
  -- for each divider found
  for st, sp in function () return string.find (str, div, pos, true) end do
    table.insert (arr, string.sub (str, pos, st - 1)) -- Attach chars left of current divider
    pos = sp + 1 -- Jump past current divider
  end
  table.insert (arr, string.sub (str, pos)) -- Attach chars right of last divider
  return arr
end
