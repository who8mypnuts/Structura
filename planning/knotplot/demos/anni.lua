--[[

rob scharein
Saturday, 2024 August 24, 20:02:36 PDT

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    vscale = 0.118
    sradius = 0.2
    background = black
    load anni1.k
    
    double
    warp install      % install the doubled knot as a warping path
  ]])

  Demo ()
  Title ("Anni Albers")

  firstcall = true

end   -- end of init block

ButtonHelp ()
ButtonStack ("toggle:"
         ..  ",grid,show ~grid"
         ..  ",draw mode,lua . ToggleDrawingMode ()"
         ..  ",fullscreen,fullscreen toggle"
            )
ButtonStack ("group 389,select on|nstrings:"
         ..  ",1,load anni1.k"
         ..  ",2,lua . make (2)"
         ..  ",3,lua . make (3)"
         ..  ",4,lua . make (4)"
         ..  ",5,lua . make (5)"
         ..  ",6,lua . make (6)"
            )
            
function make (nstrings)
  executeKP (nstrings, 1 / nstrings, [[
    braid -strings ARG1 0^222
    scale ARG2 1 1    % non-proportional scale
    warp rec2ann .5   % warp the bounding rectangle of the current knot to
                      % an annulus leaving a specified gap between the ends
    close all
    warp bbconf       % bb is the blackboard framing
    warp along        % do the warp
    colour all orange
    safe
  ]])
end


function unknots ()
  -- this creates an interesting bead pattern
  executeKP ([[
    delete all
    new=false
    colour off
    sradius = 0.2
    vscale = 0.205
    ortho
    untran
    rotate z 90
  ]])
  local r = 1
  repeat
    executeKP (string.format ("%.0f", 2 * math.pi * r), r, [[
      unknot ARG1 ARG2
      display true
    ]])
    r = r + 0.3
  until (r > 19)
  executeKP ("rotate fix")
end

requireKPbuild (5069)


if firstcall then
  firstcall = false
  executeKP ([[
    txt click 4
  ]])
end


--[[

hstart = 0.000000
hincr = 33.000000



BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
