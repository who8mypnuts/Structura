--[[

rob scharein, 18 july 2023

--]]


if demo ~= luaSource then
  demo = luaSource
  
    
  executeKP ([[
    reset all
    mode cb
    cradius = 0.12
    bradius = 0.18
    ccmode = 1
    hstart = 33
    vscale = 0.25
    silent = true
    alloc 29999
    alloc comp 8888
    silent = false
    
    txt init
    txt clobber on
    txt centre
    txt font 3
    txt fill on

    alias -e o "lua . Order ($0, $1)"
    alias -e ac "lua . AfterCreated ()"
    
    txt on

    txt push
    txt group 9
    txt centre
    txt fill on
    txt font 3
    txt c 15 "clk load" "lua . LoadBFACF()"
    txt pop
    
    txt group 9 off
    
    %if isme then "play init"
    
  ]])
 
  
  require "Lsystem"

  Demo ()
  Title ("L-systems")

end   -- end of init block


function Titles (name, order)
  Title (name)
  SubTitle ("of order " .. order)
end

Lsystem.callback = Titles

function Order (min, max)
  executeKP ([[
    txt group 342 delete
    txt push
    txt group 342
    txt font 3
    txt left
    txt fill on
    txt select on
  ]])

  local ypos = 15

  for i = max, min, -1 do
    executeKP (i, ypos, [[
      txt 15 ARG2 " ARG1 "  "lua . Lsystem.current (ARG1);lua . AfterCreated ()"
    ]])
    ypos = ypos + 30
  end
  
  executeKP (ypos, [[
    txt fill off
    txt 10 ARG1 order:
    txt pop
  ]])
end

lsys = Lsystem.defined ()  -- returns the L-systems sorted by name
                           -- pass `false' to return unsorted


executeKP ([[
  txt fill on
  txt right
  txt font 4
  txt -15 15 ? help
  txt font 3
  txt lineskip -25
  txt -15 a1.5 fullscreen "fullscreen toggle"
  txt -15 a    auto-centring "turtle centre toggle"
  txt -15 a    auto-fit "lua . autofit = not autofit echoKP ('autofit is ' .. tostring (autofit))"
  txt fill off
  txt -10 a toggle:
  txt fill on
]])

local skip = "a1.5"
for i = 1, #lsys do
  stuff = lsys [i] (-1)
  --print (stuff [1])
  executeKP (stuff [1], stuff [2], stuff [3], stuff [4], stuff [5], skip, [[
      txt -15 ARG6 ARG1 "lua . Lsystem.ARG1 (Random ('ri[ARG2/ARG3]'));ac; o ARG4 ARG5;txt group 9 off;clk stop"
    ]])
  skip = "a"
end

executeKP ([[
  txt fill off
  txt -10 a system:
]])

autofit = false

constant = 3.6

function vscale ()
  local info = lcaptureKP ("info s")
  local radius = info [#info - 1]
  return constant / radius
end

 
function CheckLoadBFACFEngine ()
  if not Safe () then return false end
  local a = mlcaptureKP ("angle")
  local angle = tonumber (a [1][3])
  print ("angle is " .. angle)
  if angle < 89 or angle > 91 then return false end
  return true
end

function AfterCreated ()
  if CheckLoadBFACFEngine () then
    executeKP ([[
      txt group 9 on
      clk stop
      play 88
    ]])
  else
    executeKP ([[
      txt group 9 off
      clk stop
      play 33
    ]])
  end
  if autofit then
    executeKP ("vscale = " .. vscale())
  end
end

function LoadBFACF ()
  executeKP ([[
    clk load
    panel set clk
  ]])
  EphemeralMessage ("loaded into the BFACF Engine")
end



ShowSourceButton ()


requireKPbuild (5090)  -- for Lsystem.defined () with sorting
