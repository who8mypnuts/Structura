--[[

Version 22 January 2025

--]]

require ("UI")   -- mouse and keyboard functions moved to UI.lua, 2 August 2024, KPbuild 5066

function TitleAux (title, position, fontSize)
  executeKP (title, position, fontSize, [[
    txt push
    txt on
    txt fill off
    txt centre
    txt font ARG3
    txt c ARG2 "ARG1"
    txt pop
  ]])
end

function Title (title)
  TitleAux (title, -20, 4)
end

function SubTitle (title)
  TitleAux (title, -40, 3)
end

function BotTitle (title)
  TitleAux (title, 12, 4)
end

function ButtonAux (title, position, action)
  if action == nil then
    echoKP ("requires an action to be specified for button `" .. title .. "'")
    return
  end
  
  executeKP (title, position, action, [[
    txt push
    txt on
    txt fill on
    txt centre
    txt font 3
    txt c ARG2 "ARG1" "ARG3"
    txt pop
  ]])
end

function Button (title, action)
  ButtonAux (title, -20, action)
end

function BotButton (title, action)
  ButtonAux (title, 12, action)
end

function Random (kind)
  return tonumber (captureKP ("echo \\" .. kind))
end

function FlipCoin ()
  local p = Random ("rr100")
  if p < 50 then
    return true
  else
    return false
  end
end

function RollDie (numberSides)   -- 3 dec 2023
  return Random ("ri[1/" .. numberSides .. ']')
end

function Interpolate (A, B, p)
  return (1.0 - p) * A + p * B
end

function InterpolateLog (A, B, p)
  if A <= 0 or B <= 0 then return nil end
  local lA = math.log (A)
  local lB = math.log (B)
  return math.exp ((1.0 - p) * lA + p * lB)
end

function Safe ()
  -- shouldn't I be able to just return the capture value?
  if captureKP ("safe -s") == "true" then
    return true
  else
    return false
  end
end

-- see http://lua-users.org/wiki/NumbersTutorial
function Thickness ()
  local stuff = tcaptureKP ("thickness")
  return tonumber (stuff [2])
end

function ThicknessFull ()
  return tcaptureKP ("thickness full")
end


function Colour (name)
  local stuff = tcaptureKP ("colour -lookup " .. name)
  return stuff [0] .. " " .. stuff [1] .. " " .. stuff [2]
end


function ShowLuaSource ()
  executeKP ('file show "' .. luaSource .. '"')
  executeKP ('txt delete "show Lua source"')
end

function ShowSourceButton ()
  --if not luaDebug then return end   removed 20 july 2023
  
  executeKP ([[
    txt push
    txt fill on
    txt font 3
    txt expire 3
    txt right
    txt delete "show Lua source"
    txt -12 -19 "show Lua source" "lua . ShowLuaSource ()"
    txt pop
    tfunction 2.2 "display true"
  ]])
end

--EphemeralMessage_yPos = "c"
EphemeralMessage_display = 4.1

-- version 5 April 2024, takes any number of arguments

function EphemeralMessage (...)
  if #{...} == 0 then return end
  local spacing = 25
  local y = -5 + spacing * (#{...} - 1) / 2
  local expire = EphemeralMessage_display
  
  executeKP ([[
    txt push
    txt fill off
    txt font 4
    txt centre
  ]])
  
  for _,v in pairs({...}) do
    executeKP ("c" .. y, v, expire, [[
      txt expire ARG3
      %echo c ARG1 "ARG2"
      txt c ARG1 "ARG2"
    ]])
    y = y - spacing
    expire = expire + 0.4
  end
  
  executeKP (expire, [[
    txt pop
    tfunction ARG1 display
  ]])
end

EphemeralMessage2 = EphemeralMessage


function Choose (things, probabilities)
  local thing, prob = explode (" ", things), explode (" ", probabilities)
  if #thing ~= #prob then return false end
end

  
function DoUntil (whatToDo,       -- what to do each step, should be a function
                                  -- requiring no arguments and returning nothing
                  successTest,    -- a function requring no arguments, returning true or false
                  timeLimit,      -- time limit in seconds, use 0 to unlimit
                  statusCallback) -- function taking three arguments: time taken, number of steps, boolean value
  local startTime = timeKP ()
  local timeTaken
  local didTimeOut = false
  local steps = 0
  if timeLimit == 0 then timeLimit = 1123456789 end  -- 35.6 years
    
  local co = coroutine.create (
    function ()
      repeat
        whatToDo ()
        steps = steps + 1
        timeTaken = timeKP () - startTime
        if timeTaken > timeLimit then
          didTimeOut = true
        end
        coroutine.yield ()
      until (successTest () or didTimeOut)
      if statusCallback ~= nil then
        statusCallback (timeTaken, steps, didTimeOut)
      end
    end
  )
  
  function DoUtilStep ()
    if coroutine.status (co) == "dead" then
      executeKP ("idle")
    else
      coroutine.resume (co)
    end
  end
  
  executeKP ('idle "lua . DoUtilStep ()"')

end

function commify (p)   -- 17 March 2025, KPbuild 5092
  p = tostring (p)     -- add commas separating blocks of three digits 
  local s = ''
  for i = #p, 1, -1 do
    s = charAt (p, i) .. s
    if (#p - 2 - i) % 3 == 0 and i ~= 1 then
      s = ',' .. s
    end
  end
  return s
end

function Plural (kount, noun)
  if tonumber (kount) == 1 then
    return kount .. " " .. noun
  else
    if ends_with (noun, "y") then
      noun = string.sub (noun, 1, -2) .. "ie"
    end
    return kount .. " " .. noun .. "s"
  end
end

function ends_with (str, ending) -- http://lua-users.org/wiki/StringRecipes
   return ending == "" or str:sub (-#ending) == ending
end

function TestPlural ()
  print (Plural (0, "thing"))
  print (Plural (1, "thing"))
  print (Plural (2, "thing"))
  print (Plural (0, "energy"))
  print (Plural (1, "energy"))
  print (Plural (2, "energy"))
  print (Plural (0, "y"))
  print (Plural (1, "y"))
  print (Plural (2, "y"))
end

function RequireKLE (minVersion)  -- added KPbuild 5016
  local info = lcaptureKP ("lua version")
  if tonumber (info [6]) < minVersion then
  executeKP (minVersion, info [6], [[
    panic requires at least KLE version ARG1, you are running ARG2
  ]])
  end
end


function RerunDemo ()
  --executeKP ('lua run "' .. luaSource .. '"')
end


function echoTable (tab)
  for i = 1, #tab do
    echoKP (tab [i] .. " ")
  end
  echoKP ("\n")
end



function printTable (t, sp)
  if sp == nil then sp = "\n" end
  local out = ""
  for k, v in pairs (t) do
    out = out .. v .. sp
  end
  print (out)
end
      
  
function charAt (str, pos)
  return string.sub (str, pos, pos)
end


function gcd (a, b)     -- greatest common divisor
  if (b == 0) then
    return a
  else
    return gcd (b, a % b)
  end
end

function lcm (n, m)     -- least common multiple
  return math.floor ((n * m) / gcd (n, m))
end



local namedColour = {}

function RandomNamedColour ()
  if #namedColour == 0 then
    local lc = mlcaptureKP ("colour list")
    print ("loading colour names")
    for i = 1, #lc do
      table.insert (namedColour, lc [i][4])
    end
  end
  return namedColour [Random ("ri[1/" .. #namedColour .. "]")]
end

local readPath = {}

function ReadFileAbsolute (absolutePath)
  print ("reading `" .. absolutePath .. "'")
  local file = io.open (absolutePath, "r")
  if file then
    local content = file:read "*a" -- *a or *all reads the whole file
    file:close ()
    return content
  else
    echoKP ("couldn't open file `" .. absolutePath .. "'")
    return nil
  end
end

function ReadFile (filename)   -- merge with above
  if charAt (filename, 1) == '/' then  -- absolute path
    return ReadFileAbsolute (filename)
  end
  
  if #readPath == 0 then
    --print ("init readPath")
    readPath = explode (":", captureKP ("path read"))
  end

  for i = 1, #readPath do
    local fullPath = readPath [i] .. "/" .. filename
    --print ("looking for " .. fullPath)
    local file = io.open (fullPath, "r")
    if file then
      local content = file:read "*a" -- *a or *all reads the whole file
      file:close ()
      return content
    end
  end
  
  echoKP ("couldn't open file `" .. filename .. "'")
  return ""
  
end


function PrintArgs ()    -- added 20 october 2023
  if (#arg > 0) then
    echoKP (Plural (#arg, "argument"))

    for i = 1, #arg do
      echoKP (i .. ": `" .. arg [i] .. "'")
    end
  end
end

function ButtonHelp (fun)    -- 1 december 2023
  if fun == nil then         -- optional argument added 4 aug 2024
    fun = "lua do ShowHelp"  -- standard-map.lua uses a custom help
  end

  executeKP (fun, [[
    txt push
    
    txt right
    txt lineskip -25

    txt font 4
    txt fill on
    txt -14 14 ? "ARG1"

    txt pop
    
  ]])
end

local sideButtonStack = "right"  -- 10 december 2023
local yButtonStack = 15

function ButtonStack (stack,       --  1 december 2023
                      separator)   -- 15 november 2024
  if separator == nil then separator = ',' end
  local nnn = explode ("|", stack)  -- 21 january 2024
  local thing = nil
  local options = ""
  local leftHack = false
  
  --print ("size of nnn is " .. #nnn)
  if #nnn == 1 then
    thing = nnn [1]
  elseif #nnn == 2 then
    thing = nnn [2]
    options = "\n"
    local op = explode (separator, nnn [1])
    for o = 1, #op do
      --print (o .. ": " .. op [o])
      options = options .. "txt " .. op [o] .. "\n"
    end
  else
    echoKP ("bad ButtonStack `" .. stack .. "'")
    return
  end
    
  local t = explode (separator, thing)
  if #t == 1 then
    sideButtonStack = t [1]
    yButtonStack = 15
    --print ("sideButtonStack set to " .. sideButtonStack)
    return
  end
  
  local x15 = -15
  local x10 = -10
  if sideButtonStack == "left" then
    x15 = 15
    x10 = 10
    leftHack = true
  end
  
  --print ("stack options are:>>" .. options .. "<<<\n")
  
  executeKP (sideButtonStack, options, [[
    txt push
    txt ARG1
    txt lineskip -25

    txt font 3
    txt fill on
    
    ARG2
  ]])
  

  --print ("thing size is ".. #t)
  --printTable (t)
  
  local lineskip = "a1.5"
  
  for i = #t - 1, 2, -2 do
    --print ("x: " .. t [i] .. " " .. t [i + 1])
    executeKP (lineskip, t [i], t [i + 1], x15, [[
      txt ARG4 ARG1 "ARG2" "ARG3"
    ]])
    lineskip = "a"
  end
  
  executeKP (t [1], x10, [[
    txt fill off
    txt phantom
    txt ARG2 a "ARG1"
    txt pop
  ]])

  if leftHack then
    --executeKP ('txt push;txt fill off;txt 15 .01 " ";txt pop')
  end
end

function ButtonAutoHide (Tmin, Tmax)
  executeKP (Tmin, Tmax, [[
    txt hideall ARG1 ARG2
    txt autohide on
  ]])
end

 

function RotateAxisUp (which)
  -- rotate the view about the centre of the window so the chosen axis is pointing up
  local axis = explode (",", "1 0 0,0 1 0,0 0 1")
  local top = lcaptureKP ("vpproject " .. axis [which])
  local bot = lcaptureKP ("vpproject 0 0 0")
  if top [1] == bot [1] and top [2] == bot [2] then
    EphemeralMessage (axis [which] .. " axis is pointing at camera, can't do it!")
    return
  end
  local angle = math.deg (math.atan (top [2] - bot [2], top [1] - bot [1]))
  executeKP (90 - angle, [[
    echo rotate k ARG1
    rotate k ARG1
  ]])
end
 

function rotateRandomXY ()
  -- keeps the x and y axes parallel with window bounds
  -- and the z-axis perpendicular with the screen
  -- 16 february 2024
  executeKP (chooseKP ("xy yx xY Yx Xy yX XY YX"), [[
    rotate ARG1
  ]])
end


function ToggleDrawingMode ()
  if captureKP ("mode") == "mode s" then
    executeKP ("mode cb")
  else
    executeKP ("mode s")
  end
end


function decimalTime ()   -- added 26 August 2024, KPbuild 5069
  local hms = explode (':', lcaptureKP ("date")[5])
  return hms [1] + hms [2] / 60 + hms [3] / 3600
end

-- check to see if we are running in graphics or non-graphics mode
-- added 1 November 2024, KPbuild 5079
local winfo = mlcaptureKP ('winfo')
if winfo ~= nil and #winfo == 4 then
  graphicsmode = true
else
  graphicsmode = false
end



function requireKPbuild (buildRequired)
  -- returns true if KnotPlot build is recent enough or false if not
  -- returning a value added 24 April 2024, KPbuild 5058
  
  local build = tonumber (lcaptureKP ("version s")[1])
  if build < buildRequired then
    if not graphicsmode then    -- 22 january 2025, KPbuild 5086
      executeKP ('panick this script requires a newer version of KnotPlot, build ' .. buildRequired)
    end
    executeKP ([[
      tfunc 7 "txt delete all"
    ]])
    EphemeralMessage (
                      "this script requires a newer version of KnotPlot, build " .. buildRequired,
                      "you are running build " .. build,
                      "  ",
                      "this script requires a newer version of KnotPlot, build " .. buildRequired,
                      "you are running build " .. build,
                      "  ",
                      "this script requires a newer version of KnotPlot, build " .. buildRequired,
                      "you are running build " .. build,
                      "  ",
                      "this script requires a newer version of KnotPlot, build " .. buildRequired,
                      "you are running build " .. build
                      )
    return false
  end
  
  return true
end


function vscaleFit (scaleFactor)   -- added 14 November 2024, KPbuild 5080
  -- compute an appropriate vscale to fit the
  -- knot currently loaded into the view window
  if scaleFactor == nil then scaleFactor = 4 end
  local info = lcaptureKP ("info s")
  if paramKP ('ncomps') == 0 then
    echoKP ('nothing loaded')
    return nil
  end
  local radius = tonumber (info [#info - 1])
  return scaleFactor / radius
end

function isme ()   -- added 29 November 2024, KPbuild 5081
  if captureKP ('if isme then "echo true"') == "true" then
    return true
  else
    return false
  end
end

function createWithNcomps (com,               -- execute this command until
                           minComp, maxComp)  -- minComp <= number of components <= maxComp
  local timeOut = timeKP () + 2               -- timeout after 2 seconds
  if minComp == nil then                      -- added 29 November 2024, KPbuild 5081
    minComp = 1
  end
  if maxComp == nil then
    maxComp = minComp
  end
  print (minComp, maxComp)
  repeat
    executeKP (com)
    local ncomps = paramKP ("ncomps")
  until (timeKP () > timeOut or minComp <= ncomps and ncomps <= maxComp)
end
