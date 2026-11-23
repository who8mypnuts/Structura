--[[

rob scharein
Wednesday, 2024 July 31, 10:44:51 PDT

--]]

require "Vector3"

Dynamics = {}

function speedInit ()
  Dynamics.speedTable = {}
  Dynamics.speedAverage = 0
  Dynamics.speedMin = 0
  Dynamics.speedMax = 0
  Dynamics.speedCallback = nil
  Dynamics.speedEM = ""
  Dynamics.speedMax = 0
  Dynamics.speedMin = 99999
  Dynamics.speedCompmin = -1
  Dynamics.speedCompmax = -1
  Dynamics.speedTable = {}
end

speedInit ()

local speedCallback = nil

function Dynamics.speedCallback (fun)
  speedCallback = fun
end

local T0 = 0
local timeInterval = 0
local coords_before = {}
local coords_after = {}

local function distanceMoved ()
  if #coords_before ~= #coords_after then
    echoKP ("size mismatch (" .. #coords_before .. " != " .. #coords_after .. ')')
    return ""
  end

  local sum = 0
  speedInit ()
  
  for i = 1, #coords_before do
    local locb = Vector3.new (coords_before [i][1],
                              coords_before [i][2],
                              coords_before [i][3])
    local loca = Vector3.new (coords_after [i][1],
                              coords_after [i][2],
                              coords_after [i][3])
                              
    local distance = Vector3.distance (locb, loca)
    local speed = distance / timeInterval

    table.insert (Dynamics.speedTable, {distance, speed})

    if speed < Dynamics.speedMin then
      Dynamics.speedMin = speed
      Dynamics.speedCompmin = i - 1
    end
    
    if speed > Dynamics.speedMax then
      Dynamics.speedMax = speed
      Dynamics.speedCompmax = i - 1
    end

    sum = sum + speed
  end
  
  Dynamics.speedAverage = sum / #coords_before
  local message = string.format ("average %.2f min %.2f (%d) max %.2f (%d)",
                                 Dynamics.speedAverage,
                                 Dynamics.speedMin, Dynamics.speedCompmin,
                                 Dynamics.speedMax, Dynamics.speedCompmax)

  return message
end

function Dynamics.speed (deltaT)
  if deltaT == 'check' then
    coords_after = mlcaptureKP ('coords cofm')
    timeInterval = timeKP () - T0

    if speedCallback ~= nil then
      Dynamics.speedEM = distanceMoved ()
      speedCallback ()
    end
    return
  end

  coords_before = mlcaptureKP ('coords cofm')  -- should allow last as well, or maybe new option cofm
                                               -- info -full m
                                               -- gives the same data as
                                               -- coords cofm
  
  deltaT = tonumber (deltaT)
  if deltaT == nil or deltaT <= 0.05 then deltaT = 0.05 end
  T0 = timeKP ()
  executeKP (deltaT, [[
    tfunction ARG1 "lua . Dynamics.speed ('check')"
  ]])
end

return Dynamics

