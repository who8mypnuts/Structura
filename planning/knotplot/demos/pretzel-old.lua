--[[

rob scharein
Thursday, 2024 September 19, 19:58:07 PDT

--]]


executeKP ([[
  reset all
  txt on
  txt clobber on
  tangle 6r6r#4zr#3r#N
  about z 180
  reflect z
  ortho
  ago 33
  sradius = 0.3
  refine 7
  save |pretzel
]])

Demo ()
BotButton ("rerun", "lua rerun")

ButtonHelp ()
ButtonStack ("toggle:"
         ..  ",grid,show ~grid"
         ..  ",draw mode,lua . ToggleDrawingMode ()"
         ..  ",fullscreen,fullscreen toggle"
            )
	    

function warp (comp, scale)
  executeKP (comp, scale, [[
    load |pretzel
    keep ARG1
    double
    warp bbconformal
    warp install
    braid -strings 3 0^99
    scale ARG2 1 1
    warp rec2ann 1
    close all
    warp along
    save |ARG1
  ]])
end

warp (0, 1)
warp (1, 2)
warp (2, 2)

executeKP ([[
  load |0
  load combine |1
  load combine |2
  scale 4
  refine equilateral
  centre
  vscale = 0.11
  safe
  xing
  meta -info
]])

  
