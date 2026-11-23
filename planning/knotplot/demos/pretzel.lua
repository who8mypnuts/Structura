--[[

rob scharein
Thursday, 2024 September 19, 19:58:07 PDT

--]]


function showStuff ()
  executeKP ([[
    display true
    nap 0.5
  ]])
end

executeKP ([[
  reset all
  txt on
  txt clobber on
  tangle 6r6r#4zr#3r#N 
  about z 180          % changes the embedding, unlike the `rotate' command which changes the camera view
  reflect z
  ortho                % switch to an orthographic projection from the default perspective projection
  lua . showStuff ()   % use `lua .' to call a Lua function from the KnotPlot side
  ago 33               % `atomic-go', doesn't relax in the background like the regular `go'
  sradius = 0.3        % this will affect the spacing between the components after a `double' command
  refine 7             % refine the number of beads by a factor of 7
  lua . showStuff ()
  save |pretzel        % filenames beginning with | are saving internally to KnotPlot
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
  -- the executeKP () function can take an arbitrary number of arguments
  -- which are numbered starting at 1 (following the Lua convention)
  --         ARG1  ARG2
  executeKP (comp, scale, [[
    load |pretzel
    keep ARG1              % delete all components except the one numbered `comp'
    double                 % double the current knot, spacing depends on the current value of sradius
    warp bbconformal       % warp using the blackboard framing
    warp install           % install the current 2-component link as a warping path
    braid -strings 3 0^99  % 3-string braid with 99
    scale ARG2 1 1         % scale only in the x-direction by value of `scale'
    warp rec2ann 1         % warp a rectangle to an annulus, leaving a space of 1
    close all              % close all components
    warp along             % warp the tubular knot along the warping path
    save |ARG1             % save internally to KnotPlot
  ]])
end


-- triple each component separately
warp (0, 1)
showStuff ()
warp (1, 2)
showStuff ()
warp (2, 2)
showStuff ()

executeKP ([[
  load |0
  load combine |1
  load combine |2
  scale 4
  refine equilateral
  centre
  vscale = 0.11
  gauss pretzel.txt
  safe
  xing
  meta -info    % writes META info into the knot file
  meta myKey "some kind of value"
  save pretzel.k
]])

  
