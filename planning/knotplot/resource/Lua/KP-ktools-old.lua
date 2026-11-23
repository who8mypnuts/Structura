print ("running KP-ktools")
  
verbose = true
if paramKP ("verbose") > 1 then verbose = true end

arch = lcaptureKP ("arch")
platform = arch [1]
cpuType = arch [2]
dir = mlcaptureKP ("path -X")

local ext = ""
if platform == "win32" then ext = ".exe" end

if jhomfly == nil then
  if verbose then print ("\n\nlooking for jhomfly executable") end
  for i = 1, #dir do
    exe = dir [i][1] .. "/" .. "jhomfly-" .. cpuType .. ext
    if verbose then print ("looking for " .. exe) end
    if FileExists (exe) then
      if verbose then print ("found " .. exe) end
      jhomfly = exe
      break
    else
      if verbose then print ("not there") end
    end
  end
else
  if verbose then print ("jhomfly set to " .. jhomfly) end
end

if platform == "macOS" then
  cpuType = "x86_64"  -- ARM Macs will run x86_64 using Rosetta
end

if jidknot == nil then
  if verbose then print ("\n\nlooking for jidknot executable") end
  for i = 1, #dir do
    exe = dir [i][1] .. "/" .. "jidknot-" .. cpuType .. ext
    if verbose then print ("looking for " .. exe) end
    if FileExists (exe) then
      if verbose then print ("found " .. exe) end
      jidknot = exe
      break
    else
      if verbose then print ("not there") end
    end
  end
else
  if verbose then print ("jidknot set to " .. jidknot) end
end




