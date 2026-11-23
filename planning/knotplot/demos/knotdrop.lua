--[[

rob scharein
Wednesday, 24-Jan-24 00:14:08 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    sradius = 0.6
    cradius = 0.3
    bradius = 0.4
    tanmag = 0.013
    
    scenery on
    scenery dscale .2
    
    rotate x -55   % rotate view, can also use left mouse button
                   % in view window (no affect on dynamics)
    vscale = 0.2   % scale view, can also use right mouse button
                   % in view window  (no affect on dynamics)
    grsize=20      % size of grid
    show grid
    
    set shadow 1
    
    drag = on
    tanmag = 0.013
    
    txt push
    txt group 1022
    txt centre
    txt c 44 "click on the knot to drag it around"
    %txt c 44 "this will be easier using draw mode `cb'"
    txt pop
    txt group 1022 off
    
    
    new = false
    
    alias -e selectCallback "lua . SelectCallback ($0)"
    select callback selectCallback
    
 
    
  ]])

  Demo ()
  --RequireKLE (16)    -- for variadic EphemeralMessage function
  RequireKLE (17)   -- for relax callback
  
  Title ("Dropping Knots")
  SubTitle ("preparing knot...")
  BotButton ("new knot", "lua do knotdrop")
  extraCom = "noop"
  
  function TestLeapCallback ()
    local tips = fingerTipsKP ()
  end
  
  function Leap1 ()
    executeKP ([[
      lua relax TestLeapCallback
    ]])
  end
  
  function Leap2 ()
  end

  firstrun = true
  
  l = mlcaptureKP ("leap connect")
  if #l == 3 and l [1][1] == 'Connected!' and l [3][1] == 'connected' then
    leap = true
  else
    leap = false
  end

  
  ButtonHelp ()
  ButtonStack ("toggle:,grid,show ~grid,axes,show ~axes,tanforce,lua . ToggleTangentForce(),fullscreen,fullscreen toggle")
  ButtonStack ("action:,ID,lua . ID(),stop,lua . Stop(),keep 0,keep 0,centre,lua . CentreXY()")
  ButtonStack ("select on,group 108,phantom cb|draw mode:,s,mode sS;select scale 1.8,cb,mode cbS;select scale 1")
  ButtonStack ("rotate:,xy,rotate xy,yz,rotate yz,zx,rotate zx,z-up,lua . RotateAxisUp(3)")

  ButtonStack ("left")
  executeKP ('txt push;txt fill off;txt 15 .01 " ";txt pop')
  ButtonStack ("select on,group 102|extra:,none,lua . Extra (1),circle,lua . Extra (2),line,lua . Extra (3)")
  ButtonStack ("select on,group 776|drop:"
           ..  ",trefoils,lua . PrepareKnot = PrepareTrefoil"
           ..  ",all knots,lua . PrepareKnot = PrepareSomeKnot"
              )
            

  if leap then
    ButtonStack ("group 3345|Leap:"
           ..  ",1,lua . Leap1 ()"
           ..  ",2,lua . Leap2 ()"
              )
  end


  ButtonAutoHide (5,7.4)
  
  executeKP ([[
    % don't want these buttons to autohide
    txt push
    txt group 153
    txt hide 9999
    txt centre
    txt font 4
    txt c -70 "press and hold the w-key to pull the knot towards you"
    txt c -95 "press and hold the q-key to push it away from you"
    txt pop
    txt group 153 off
  ]])
  
end   -- end of init block


relaxing = false

on_off = {"on", "off"}

function SelectCallback (what)
  executeKP (on_off [what + 1], [[
    txt group 153 ARG1
  ]])
end

function ToggleTangentForce ()
  if tanforce then
    executeKP ("tanforce = off;drag = on;panel draw")
    EphemeralMessage ("drag force on", "tangent force off")
  else
    executeKP ("tanforce = on;drag = off;panel draw")
    EphemeralMessage ("tangent force on", "drag force off")
  end
  tanforce = not tanforce
end
  
tanforce = true   -- this is the Lua variable, not to be confused with the KnotPlot parameter
ToggleTangentForce ()


extra = explode (",", "noop,unknot \\ri[6/22] \\rr[4/9],line from 0 -10 0 to 0 10 0")

function Extra (what)
  extraCom = extra [what]
end

blurtcentre = 2
function CentreXY ()
  local m = "centring only in x and y directions"
  if blurtcentre < 0 then m = "" end
  executeKP (m, [[
    echo ARG1
    centre xy
  ]])
  blurtcentre = blurtcentre - 1
end

function Stop ()
  executeKP ([[
    go 0
    txt group 1022 off
  ]])
  relaxing = false
end

function ID ()
  executeKP ("save |tmp;keep 0")
  local id = captureKP ("id")
  executeKP ("load |tmp")
  local m = " "
  
  if relaxing then
    m = "click on the `stop' button to stop relaxing"
  end
  executeKP (id, m, [[
    echo
    echo knot ID is ARG1
    echo ARG2
    go 0
  ]])
  EphemeralMessage (id)
  if relaxing then  -- start relaxing again
    executeKP ("go")
  end
end

function PrepareTrefoil ()
  relaxing = false
  local r = "nop"
  local h = "left"
  if FlipCoin () then
    r = "reflect r"
    h = "right"
  end
  
  local nb = Random ("ri[77/222]")
  local st = h .. "-handed trefoil with " .. nb .. " beads"
  
  executeKP (r, st, nb, extraCom, [[
    delete all
    stusplit = 0
    txt group 1022 off
    tfunc reset
    verbose = 0
    torus 2 3 ARG3
    swirl \rr+-55
    project random
    %echo operation is `ARG1'
    ARG1
    
    echo
    echo ARG2
    translate 0 0 12
    
    echo "ARG4"
    ARG4
    
    if ncomp == 2 then "about z \rr360 1"
    
    %rmass all 1
    %rmass 1 0
    
    
    verbose = 1
  ]])
  SubTitle (st)
end

function CheckForToothpaste ()
  local nb = paramKP ("nbeads")
  if nb > 200 then
    executeKP ([[
      delete 0
    ]])
    EphemeralMessage ("oh no, something has happened!",
                      " ", " ", " ", " ", " ", " ", " ")
  end
end

function PrepareSomeKnot ()
  
  relaxing = false
  
  
  executeKP (extraCom, [[
    delete all
    stusplit = 1
    txt group 1022 off
    tfunc reset
    
    tfunc 1 "lua . CheckForToothpaste ()" 0 rep 1
    verbose = 0
    knot 1
    swirl \rr+-55
    project random

    translate 0 0 \rr[12/17]
    
    echo "ARG1"
    ARG1
    
    if ncomp == 2 then "about z \rr360 1"
    
    %rmass all 1
    %rmass 1 0
    

    verbose = 1
  ]])
  SubTitle (" ")
end


function DropIt ()
  executeKP (paramKP ("sradius"), [[
    % set up dynamics

    3dop gravity 0 0 -1   % direction `gravity' acts in
    gravity = on          % turn `gravity' on
    velforce = true       % turn on velocity damping force
    wall = true           % enable wall forces
    walindex = 2          % wall perp to z axis (use 0 for perp to x,
                          % 1 for perp to y)
    walvalue = ARG1       % wall at level equal to sradius
    coll n                % don't allow knot to pass thru itself or others

    dstep = 3             % increase this if your computer has a slow
                          % graphics card but a fast CPU

    force 1               % allow beads to have inertia

    go                    % relax `forever'
    
    tfunc 2 "txt group 1022 on"
  ]])
  
  relaxing = true
end

if firstrun then
  c = 'none'
  if leap then c = 'circle' end
  
  executeKP (c, [[
    txt click s
    txt click ARG1
    txt click trefoils
  ]])
  
  firstrun = false
end


PrepareKnot ()
DropIt ()

ShowSourceButton ()

requireKPbuild (5067)

--[[

BEGIN HELP

Drop knots onto the xy-plane using the gravity force!

Stuff to try:
  -- Hover the mouse over the knot until you see a wire-frame
     icosahedron appear.  Then click and drag to move the knot
     around.  You should be able to do perform Reidemeister moves
     and simplify any knot to the minimal number of crossings.
     
  -- Use the rotate button stack to choose between a number of
     views.  There are four views aligned with the coordinate axes.
     The z-up button is useful for aligning the z-axis to exactly
     vertical from whatever rotation you currently have.
     
  -- There are some actions to try:
       -- ID to identify the knot type
       -- stop to stop the relaxation
       -- keep 0 to get rid of all but component 0
       -- centre to centre everything in the xy-directions (but not z)

Left side buttons:

  -- Add something extra in addition to the knot. The choices
     are a circle and a line. You can click and drag on the circle
     to help simpify the knot.  Try dragging it underneath the
     knot. You can pick up the line or the circle and drop it
     on the knot somewhere. This will agitate the knot in various
     ways and can be quite a lot of fun.
     
  -- The demo starts by dropping swirled trefoils. These have
     interesting shapes when dropped onto the plane and they
     can be quite fun to simplify by dragging the knot around.
     
     You can also use `all knots' to drop a randomly chosen knot from
     the catalogue. These are also swirled a bit which sometimes puts
     them into an unsafe position and beads start getting created
     like crazy. KnotPlot will detect and delete these bad cases.
     
  -- mode s and mode cb are actually mode sS and mode cbS,
     S is for "shadow", this is an experimental mode added 15 April 2024.
     The shadow is now only on the xy-plane, and component 0 has
     no shadow. More features will come in future versions of KnotPlot.
     The shadow's presence helps a lot when using the circle or the
     line to agitate the knot.

END HELP

--]]
