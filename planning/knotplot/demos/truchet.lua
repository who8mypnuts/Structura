--[[

rob scharein
Thursday, 2024 August 15, 11:49:24 PDT

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    function 2 "www en.wikipedia.org/wiki/Truchet_tiles"
    sradius = 0.26
    vscale = 0.16
    alias -e m "lua . Make ($0, $1)"
    silent = true
    alloc 99999
    alloc comp 9999
    silent = false
    3dop oscale .2
    label-mode = 3
    bradius = 0.12
    set oscale 0.6
    mode s
    go beadlimit 7777
    dstep = 22
    dbmin = 3
    grsize = 20
    tess colour last
    %tfunc 5 "lua . HideButtons()" 0 rep 1
    ortho
  ]])

  Demo ()
  Title ("Truchet tiles")
  SubTitle ('orthographic projection')
  --BotButton ("rerun demo", "lua rerun")

  firstcall = true
  EOfill = false
  
  require "ColourUtils"

ShowSourceButton ()

ButtonHelp ()
ButtonStack ("toggle:"
         ..  ",grid,show ~grid"
         ..  ",EO fill,lua . ToggleEOFill ()"
         ..  ",draw mode,lua . ToggleDrawingMode ()"
         --..  ",projection,lua . ToggleProjection ()"  removed 2 oct 2024
         ..  ",orientation,show ~orientation"
         ..  ",fullscreen,fullscreen toggle"
            )
ButtonStack ("action:"
         ..  ",new,lua . make()"
         ..  ",big new,lua . makeHuge()"
         ..  ",recolour,lua . make(0)"
         ..  ",delete last,delete last"
         ..  ",blobify,lua . Blobify ()"
            )
ButtonStack ("transform:"
         ..  ",CW,about z -45"
         ..  ",CCW,about z 45"
         ..  ",reflect x,reflect x"
         ..  ",reflect y,reflect y"
            )
            
ButtonStack ("left")
executeKP ('txt push;txt fill off;txt 15 .01 " ";txt pop')

ButtonStack ("select on,group background|background:"
         ..  ",black,background = black"
         ..  ",white,background = white"
         ..  ",grey,background = KnotPlotGrey"
         ..  ",random,background = random"
            )
            
ButtonStack ("select on,group tess|tess colour:"
         ..  ",last,tess colour last;echo tesselation colour is colour of last component"
         ..  ",black,tess colour black"
         ..  ",white,tess colour white"
         ..  ",lupin,tess colour Lupin"
         ..  ",random,tess colour random"
            )

end   -- end of init block

function ToggleDrawingMode ()
  -- this overrides the function defined in Demos-init.lua
  local m = explode (" ", captureKP ('mode'))
  local addE = false
  --echoKP ('\n\nmode was ' .. m [2])
  if string.sub (m [2], -1, -1) == 'E' then
    m [2] = string.sub (m [2], 1, -2)
    addE = true
  end
  if m [2] == 's' then
    m [2] = 'cb'
  else
    m [2] = 's'
  end
  if addE then m [2] = m [2] .. 'E' end
  executeKP (m [2], [[
    echo
    echo mode ARG1
    mode ARG1
  ]])
  
end

function Blobify ()
  executeKP ([[
    refine 4
    shift random
    refine equi 2
    reap 4
    go 55
  ]])
end

function mondrian ()
  ColourUtils.ColourFromSet ("Mondrian")
end

function ToggleEOFill ()
  EOfill = not EOfill
  local m = explode (" ", captureKP ('mode'))
  if EOfill then
    executeKP (m [2], [[
      echo mode ARG1E
      mode ARG1E
      untran
    ]])
  else
    executeKP (string.sub (m [2], 1, -2), [[
      echo
      echo mode ARG1
      mode ARG1
    ]])
  end
end

function MakeTiles (nbeads)
  executeKP (nbeads, 360 / (2 * nbeads), [[
    unknot ARG1 10
    about z 90
    about z ARG2
    fitto 10
    cut spin y 0
    cut spin x 0
    translate -10 -10 0
    duplicate
    reflect xy 0
    scale 0.1
    swap 0 1
    save |t1
    about z 90
    swap 0 1
    save |t2
    keep 0
    save |t3
    load |t2
    keep 1
    save |t4
    load |t1
    keep 0
    save |t5
    load |t1
    keep 1
    save |t6
  ]])
  local com = "delete bead 7;delete bead 2"
  for i = 1, 6 do
    if i > 2 then com = "delete bead 2" end
    executeKP (i, com, [[
      load |tARG1
      ARG2
      save |sARG1
    ]])
  end
end

tileset = 't'

function Make (nx, ny)
  if nx < 2 or ny < 2 then
    echoKP ("sizes must be at least 2")
    return
  end
  
  local op = "f"
  
  local function placeTile (x, y, tile)
    executeKP (x * spacing - (nx + 1),
               y * spacing - (ny + 1),
               tile, op, tileset, [[
      load |ARG5ARG3
      translate ARG1 ARG2 0
      copy ARG4
    ]])
    op = "+"
  end
  
  for y = 1, ny do
    for x = 1, nx do
      placeTile (x, y, Random ("ri[1/2]"))
    end
  end
  
  local top = {5, 4}
  local bot = {3, 6}
  for x = 1, nx do
    placeTile (x, 0,      bot [x % 2 + 1])
    placeTile (x, ny + 1, top [x % 2 + 1])
  end
  
  local right = {5, 3}
  local left = {4, 6}
  for y = 1, ny do
    placeTile (0,      y, left [y % 2 + 1])
    placeTile (nx + 1, y, right [y % 2 + 1])
  end

  executeKP (join, 0.5, [[
    % join is defined as a noop (see below),
    % so this only does the `copy t' operation
    % but doesn't join anything
    copy t
    jthresh = ARG2
    timer start
    ARG1 all
    %timer check
    jthresh = 1
  ]])
  
end

function makeHuge ()
  local T0 = timeKP ()
  Make (16 * 2, 9 * 2)
  executeKP ([[
    join grid
    swap random
  ]])
  echoKP (timeKP () - T0)
end

spacing = 2
join = "noop"

MakeTiles (20)


function make (a)  -- if an argument is supplied, ignore it, but just recolour
  local com = "noop"  -- no operation, i.e., do nothing
  if a == nil then
    Make (2 * RollDie (14), 2 * RollDie (14))
    com = "join grid"
  end
  
  executeKP (com, [[
    ARG1
    swap random
    saturation = \rr[.7/1]
    hstart = \rr360
  ]])
  
  hstart = paramKP ('hstart')
  saturation = paramKP ('saturation')
  ncomps = paramKP ('ncomps')
  hincr = 360.0 / ncomps
end


make ()

lastTime = timeKP ()

function HideButtons ()  -- not used
  local offon = "off"
  if timeKP () - lastTime < 5 then
    offon = "on"
  end
  executeKP (offon, [[
    txt group 0 ARG1
    txt group background ARG1
  ]])
end

function Minga (x, y)
  lastTime = timeKP ()
end

UI.orthoMouse (function ()
                 SubTitle ("perspective projection")
               end,
               function ()
                 SubTitle ("orthographic projection")
                end
               )


function cback (ignore,
                comp)
  -- set the hue of the orientation arrow to the
  -- complement of the hue of the component
  local hue = string.format ("%.2f", hstart + comp * hincr) + 180.0
  executeKP (hue, saturation, [[
    set colo hsv:ARG1/ARG2/1
  ]])
end


if firstcall then
  firstcall = false
  executeKP ([[
    txt click grey background
    txt click last tess
    lua draw cback
  ]])
end

requireKPbuild (5072)  -- for txt group names as strings

--[[

BEGIN HELP

Click on the `new' button in the 'action' section to get
a new tiling. Click on `recolour' to change the colours
but not the tiling. It can be interesting to repeatedly
click on the `delete last' button, especially if EO fill
is on.

Toggle EO fill to on, KnotPlot will unrotate the view and
switch to an orthographic projection because that's how the
EO fills look the best. Feel free to rotate the view to see
what's going on behind the scenes.


Press F2 to go to the Wikipedia page on Truchet tiles.





END HELP

ideas:

have different sets of tiles



--]]
