--[[

rob scharein
Monday, 13-May-24 18:20:09 UTC

--]]

KnotTheory = {}

local dt = {}
for i = 1, 26 do
  dt [tostring (2 * i)] = string.char (96 + i)
  dt [tostring (-2 * i)] = string.char (64 + i)
end

local function error (message)
  echoKP ("*** " .. message)
end

function KnotTheory.DTcodeAlpha (dtInts)  -- table of ints
  --[[
    takes a table of ints and returns the alphabetic DT code,
    like that used in Regina (the software)
    
    example usages:
    executeKP ("load 6.3")
    print (KnotTheory.DTcodeAlpha (lcaptureKP ("dowker")))
    returns DCFEAB
  
  --]]
  local adt = ""
  for k,v in pairs (dtInts) do
    v = tostring (v)
    if dt [v] == nil then
     return nil end
    adt = adt .. dt [v]
  end
  return adt
end

function KnotTheory.flypmothMaple (flypmoth)
  --[[
    - L^-4 - 3L^-2 - 2 - L^2 + M^2L^-4 + 3M^2L^-2 + 2M^2 - M^4L^-2
    1 + M^2L^-6 + M^2L^-4 - M^2L^-2 - M^2 - M^4L^-4 + M^4L^-2
    - L^2 + L^4 + L^6 + 2M^2L^2 - M^2L^6 - M^2L^8 - M^4L^4 + M^4L^6
    - 3L^-8 - 4L^-6 - M^2L^-10 + M^2L^-8 + 7M^2L^-6 - M^2L^-4 + M^4L^-8 - 3M^4L^-6 + M^4L^-4
    L^-4 + L^-2 + 1 - L^4 - L^6 - 2M^2L^-2 + 2M^2L^4 + M^4 - M^4L^2
    - M^-1L^-9 - M^-1L^-7 + ML^-9 - 5ML^-5 + 5M^3L^-5 - M^5L^-5

  --]]
  
  local maple = ""
  local terms = explode (" ", flypmoth)
  for i = 1, #terms do
    if #terms [i] == 1 then
      maple = maple .. terms [1]
    end
  end
  
  return maple
end

KnotTheory.homflyptMaple = KnotTheory.flypmothMaple

function KnotTheory.randomBraid (length,            -- if omitted, a random length is used
                                 numberOfStrings)   -- if omitted, defaults to 3
  if length == nil then length = RollDie (7) end
  if numberOfStrings == nil then numberOfStrings = 3 end
  if numberOfStrings < 2 or numberOfStrings > 26 then return nil end
  
  local braidWord = ""
  for i = 1, length do
    local g = RollDie (numberOfStrings - 1)
    if FlipCoin () then
      g = g + 64  -- upper case
    else
      g = g + 96  -- lower case
    end
    braidWord = braidWord .. string.char (g)
  end
  return braidWord
end
  

KnotTheory.braidGenerator = {"a", "b", "A", "B"}   -- table of generators

function KnotTheory.braidsLength (n,                 -- braids of length n
                                  numberOfStrings)   -- if omitted, defaults to 3
                  
                       
  --if numberOfStrings == nil then numberOfStrings = 3 end
  numberOfStrings = 3   -- only support 3 strings for now
  
  local braids = {}
  
  
  if n < 1 or n > 11 then return nil end
  local K = math.tointeger (4^n)
  for i = 0, K - 1 do
    --local word = "-strings " .. numberOfStrings .. " "
    local word = ""
    
    local M = i
    for j = 0, n - 1 do
      word = word .. KnotTheory.braidGenerator [M % 4 + 1]
      M = math.floor (M / 4)
    end
    table.insert (braids, word)
  end
  return braids
end

