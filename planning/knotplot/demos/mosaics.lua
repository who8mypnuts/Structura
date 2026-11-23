--[[

rob scharein, 2 december 2023
    
reworked 26 january 2023

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    alias mos "lua . Thing($0,$1)"
    vscale = 0.092
    
    alias -e make "lua . Make($0,$1,$2)"
    
    function 2 "www arxiv.org/abs/2306.09276"
    function 3 "www arxiv.org/abs/1602.03733"
    
    lua do mosaic init   % defines the MakeMosaic function
    
    alias t "lua . test ()"
    
  ]])

  Demo ()
  require "Primitives"
  Title ("Mosaics")
  SubTitle ("unfinished demo")
  printTableTest = printTable
  
  tile = explode (" ", "0 1 2 3 4 5 6 7 8 9 x")
  firstcall = true
  projection = "perspective"
  
  connect = {
    ["0"] = explode (" ", ". . . ."),
    ["1"] = explode (" ", ". . r b"),
    ["2"] = explode (" ", "l . . t"),
    ["3"] = explode (" ", "l b . ."),
    ["4"] = explode (" ", ". b r ."),
    ["5"] = explode (" ", "l . r ."),
    ["6"] = explode (" ", ". b . t"),
    ["7"] = explode (" ", "l b r t"),
    ["8"] = explode (" ", "l b r t"),
    ["9"] = explode (" ", "l b r t"),
    ["x"] = explode (" ", "l b r t"),
    ["n"] = explode (" ", ". . . .")
  }
  
  
  
  for k, v in pairs (connect) do
    --print ("\n" .. k)
    --printTableTest (v)
    --printTableTest (v, " ")
  end
  
    
  
end   -- end of init block

ButtonHelp ()
ButtonStack ("toggle:,grid,show ~grid,projection,lua . ToggleProjection(),fullscreen,fullscreen toggle")
ButtonStack ("extras:,intro,lua . Intro()")

ButtonStack ("action:"
            .. ",ID,lua . ID ()"
           -- .. ",relax,go"
            .. ",untran,untran"
            )

ButtonStack ("knots:"
        .. ",0.1,lua . KnotFromCode ('0.1')"
        .. ",3.1,lua . KnotFromCode ('3.1')"
        .. ",4.1,lua . KnotFromCode ('4.1')"
        .. ",5.1,lua . KnotFromCode ('5.1')"
        .. ",6.1,lua . KnotFromCode ('6.1')"
        .. ",6.3,lua . KnotFromCode ('6.3')"
        .. ",8.18,lua . KnotFromCode ('8.18')"
        .. ",0.2.1,lua . KnotFromCode ('0.2.1')"
        .. ",2.2.1,lua . KnotFromCode ('2.2.1')"
        .. ",4.2.1,lua . KnotFromCode ('4.2.1')"
        .. ",6.3.2,lua . KnotFromCode ('6.3.2')"
    --    .. ",?,lua . KnotFromCode ('?')"
    --    .. ",a,lua . KnotFromCode ('a')"
    --    .. ",b,lua . KnotFromCode ('b')"
        .. ",weave,lua . weave()"
        .. ",random,lua . RandomCode ()"

        )

--ButtonAutoHide (5, 7)

ecom = "nop"

function ThingOld (cols, rows)
  local com = "lua do mosaic"
  for r = 1, rows do
    com = com .. " "
    for c = 1, cols do
      com = com .. tile [Random ("ri[1/11]")]
    end
  end
  executeKP (com, ecom, [[
    ARG2 ARG1
    ARG1
  ]])
end

function test ()
  local scale = .5
  local offset = Vector3.new (0, 0, 0)
  local crad = 0.4
  local colour
  local s = 8
  local a = Vector3.new (-s, -s, -crad)
  local b = Vector3.new (s, -s, -crad)
  local c = Vector3.new (s, s, -crad)
  local d = Vector3.new (-s, s, -crad)
  
  executeKP ([[
    scenery on
    scenery delete
  ]])

  for t = 1, 10 do
    executeKP (t, scale, offset.x, offset.y, offset.z, [[
      load mosaic-tARG1
      scale ARG2
      echo translate ARG3 ARG4 ARG5
      translate ARG3 ARG4 ARG5
    ]])

    for comp = 1, paramKP ("ncomps") do
      if comp == 1 then
        colour = "KnotPlotOrange"
      else
        colour = "skyblue"
      end
      CylinderPath (getComponentKP (comp - 1), 0.4, 25, colour)
    end
    --Quad (a, b, c, d, "darkgrey", 1, false)
    a = Vector3.add (a, offset)
    b = Vector3.add (b, offset)
    c = Vector3.add (c, offset)
    d = Vector3.add (d, offset)
    executeKP ([[
      delete all
    ]])
    offset.x = offset.x + 9
  end
end

function weave (M, N)
  local b = false
  if M == nil then
    M = 0
    N = 0
    b = true
    echoKP ("\nuse this command to recreate:")
  end

  local mosaic = {}
  if M == 0 then M = RollDie (10) end
  if N == 0 then N = RollDie (10) end
  if b then
    echoKP ("lua . weave(" .. M .. "," .. N .. ")")
  end
  
  local s2 = "lua do mosaic "
  for n = 1, N do
    s = ""
    for m = 1, M do
      if FlipCoin () then
        s = s .. "9"
      else
        s = s .. "x"
      end
    end
    table.insert (mosaic, s)
    s2 = s2 .. s .. " "
  end
  MakeMosaic (mosaic)
  if not b then echoKP (s2) end
  executeKP ("swap random")
end

function RandomCode ()
  local c = chooseKP ("021000 28.100 3..710 03...1 003784 000340|002551 02.106 2...16 63...4 603.40 355400",
                      "1|1", "|")
  local code = ""
  for i = 1, #c do
    if charAt (c, i) == '.' then
      if FlipCoin () then
        code = code .. "9"
      else
        code = code .. "x"
      end
    else
      code = code .. charAt (c, i)
    end
  end
    
  executeKP (code, [[
    echo create this from the command line with
    echo lua do mosaic ARG1
  ]])
  MakeMosaic (explode (" ", code))
end

function Thing (cols, rows)
  local word = {}
  for r = 1, rows do
    local w = ""
    for c = 1, cols do
      w = w .. tile [Random ("ri[1/11]")]
    end
    table.insert (word, w)
  end
  MakeMosaic (word)
end

function ID ()
  local id = captureKP ("id")
  EphemeralMessage (id)
  echoKP (id)
end

function Intro ()
  for i = 1, 11 do
    for j = 1, 1 do
      Thing (i, i)
      executeKP ([[
        swap random
        display true
        nap 0.03
      ]])
    end
  end
end

if firstcall then
  --Intro ()
  firstcall = false
end

function Make (ncomps, width, height)
  local function mos ()
    Thing (width, height)
  end
  
  local function check ()
    local info = lcaptureKP ("info s")
    return tonumber (info [1]) == ncomps
  end
  
  local function info (timetaken, numsteps, timedOut)
    executeKP (Plural (numsteps, "step"), string.format ("%.1f", timetaken), [[
      echo did it in ARG1 (ARG2 seconds)
    ]])
  end
    
  DoUntil (mos, check, 99999, info)
end

function example ()
  executeKP ([[
    echo running the command
    echo MakeMosaic ({'021000', '2x7100', '37x710', '039x91', '003984', '000340'})
    echo from Lua
  ]])
  MakeMosaic ({'021000', '2x7100', '37x710', '039x91', '003984', '000340'})
end

tiles = {}

-- separate different codes for the same knot type by commas

tiles ["0.1"] = "21 34,210 3x1 034,2121 3x94 29x1 3434"
tiles ["3.1"] = "0210 29x1 3x84 0340,0210 29x1 6394 354,00210 02x91 2xxx4 39x40 03400"
tiles ["4.1"] = "02100 2x710 37x91 03984 00340,00210 02x91 2xxx4 3x940 03400"
tiles ["5.1"] = "02100 29x10 3x7x1 03x84 00340"
tiles ["6.1"] = "02100 29x10 3xx91 039x4 00340"
tiles ["6.3"] = "021000 28x100 3x9710 03x9x1 003784 000340"
tiles ["8.18"] = "002551 029106 29x916 639x94 603940 355400"
tiles ["0.2.1"]   = "0210 2xx1 3xx4 0340,0210 2xx1 3994 0340,021 274 340"
tiles ["2.2.1"]   = "0210 2x91 3xx4 0340"
tiles ["4.2.1"]   = "0210 2x91 39x4 0340"
tiles ["6.3.2"] = "002551 25x106 629x16 6639x4 395460 035540"
tiles ["?"] = "21212100 39x9x910 2x9x9x91 63434346 35555554,21212100 39x9x910 2x9xx991 63434346 35555554"
tiles ["a"] = "x9x9 9x9x x9x9 9x9x"
tiles ["b"] = "021210 2x9x91 39x9x4 2x9x91 39x9x4 034340"

function KnotFromCode (c)
  print ("c is " .. c)
  local k = explode (",", tiles [c])
  local code = k [RollDie (#k)]
  executeKP (code, [[
    echo create this from the command line with
    echo lua do mosaic ARG1
  ]])
  MakeMosaic (explode (" ", code))
end


function ToggleProjection ()
  if projection == "perspective" then
    projection = "orthographic"
    executeKP ("ortho")
  else
    projection = "perspective"
    executeKP ("persp")
  end
  SubTitle (projection .. " projection")
end

--test ()
--executeKP ("txt click 6.3")

--[[

stuff to do:

interactive editor.  click on square and possible substitutions pop up

arbitrary quad grids, as in celtic


BEGIN HELP

Things to try:
  Click on the buttons in the knots: stack to create a knot of the indicated type.
  Look in the KnotPlot Command Window to see the command used to create that knot.

References:
   
   Quantum knots and mosaics
   Samuel J. Lomonaco and Louis H. Kauffman
   Quantum Inf Process
   DOI 10.1007/s11128-008-0076-7

   Knot Mosaics with Corner Connection Tiles
   Aaron Heap, Una Donovan, Riley Grossman, Nickolas Laine, Connor McDermott,
   Marcus Paone, and Drew Southcott
   https://arxiv.org/abs/2306.09276
   (Press F2 to go to this web page)
   
   Knot mosaic tabulation
   Hwa Jeong Lee, Lewis D. Ludwig, Joseph S. Paat, Amanda Peiffer
   https://arxiv.org/abs/1602.03733
   (Press F3 to go to this web page)
   
   
END HELP

--]]
