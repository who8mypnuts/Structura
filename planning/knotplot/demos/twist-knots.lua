--[[

rob scharein
Monday, 17-Jun-24 02:51:27 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    stusplit = 1
    sradius = 0.6
    txt on
    txt clobber on
    rotate z 90
    txt push
    txt group twist
    txt centre
    txt font 4
    txt c c-190 "twist:"
    txt fill on
    txt c-22 c-222 "-" "lua . Twist (-1)"
    txt c+22 c-222 "+" "lua . Twist (1)"
    txt pop
    
    txt push
    txt group warp
    txt centre
    txt fill on
    txt c c-300 "warp and clasp" "lua . Warp ()"
    txt group warp off
    txt group ID
    txt font 4
    txt c c-322 ID "lua . ID ()"
    txt group ID off
    txt pop
    
    txt push
    txt group topText
    txt centre
    txt font 3
    txt lineskip 20
    txt c -50 file doc/twist.txt
    txt pop

  ]])

  Demo ()
  Title ("Creating a twist knot")
end   -- end of init block

ButtonHelp ()
ButtonStack ('toggle:'
          .. ',draw mode,lua . ToggleDrawingMode2()'
          .. ',fullscreen,full toggle'
            )
            
BotButton ("rerun demo", "lua rerun")
   
twist = 0
didWarp = false

function ToggleDrawingMode2 ()
  ToggleDrawingMode ()
  
  
  if didWarp then
    executeKP ([[
      bradius = 0.18
      cradius = 0.1
    ]])
  else
    executeKP ([[
      sradius = 0.6
      bradius = 0.7
      cradius = 0.53
    ]])
  end
end

function Twist (n)
  twist = twist + n
  executeKP (twist, n * 9, [[
    txt group warp on
    txt group topText off
    echo twist is ARG1
    #10 swirl end ARG2;display t
  ]])
  SubTitle ("twist is " .. twist)
end

function Warp ()
  didWarp = true
  executeKP ([[
 
    txt group warp off
    txt group twist off
    Drawing = false
    silent = true
    save |tw1
    reflect yx
    warp rec2ann 102
    save |tw2
    load |tw1
    Drawing = true
    deform to |tw2 55
    Drawing = false
    frame comm "load |tw1;warp rec2ann %d;disp t"
    frame 102 to -6 step 4
    Drawing = true
    scale keep .3
    go
    tfunction 1 "txt group ID on"
    bradius = 0.18
    cradius = 0.1

  ]])
end
            
function makeBraid (n)
  executeKP (n, [[
    Drawing = off
    braid -strings 2 0^ARG1
    scale 2 1 1
    join all
    split 4
    ago 20
    vscale = 0.06
    Drawing = on
    swirl end 45
  ]])
end

function ID ()
  local id = "knot ID is " .. captureKP ("id")
  EphemeralMessage (id)
  echoKP (id)
end

makeBraid (14)

requireKPbuild (5072)  -- txt group names as strings

--[[

BEGIN HELP

Twist knots are a family of knots obtained by
twisting the ends of an unknot, and then connecting
the ends via a clasp.  Click on one of the twist
buttons '-' or '+' below a few times. When you are
done twisting, click on `warp and clasp' button to
make the twist knot.

After warping and clasping, an `ID' button will
appear allowing you to identify the knot type.

Note that if you over-twist, you will get a bad
embedding and the knot ID will be invalid.





END HELP

--]]
