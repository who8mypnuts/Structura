--[[

rob scharein, 13 October 2022
in the Public Domain

--]]

Demo ()

if demo ~= "walk" then
  demo = "walk"
  executeKP ([[
    reset all
    vscale = 0.06
    allocate 20000
    rotate x \rr[-50/-65]
  ]])
  if FlipCoin () then
    executeKP ("rotate y 180")
  end
end

executeKP ([[
  #4 echo
  txt init
  txt centre
  txt on
  txt clobber on
  txt fill on
  
  silent = true
  
  load mscl/3.1
  translate 4 -65 0
  clk load    % trefoil now in BFACF Engine
  show bfacf
  mode 0

  clk clear 30
  sradius = 1
  
  % clear out the centre of the labyrinth
  delete all
  new = false
  frame command "unknot 10 %d"
  frame 1 to 20
  scale 0.4
  save |tmp
  translate 0 1 0

  load ravenna.k

  txt fill off
  txt font 4
  txt c 10 "Labyrinth in San Vitale, Ravenna, Italy"
  txt font 3

  fitto 65
  mode s
  % standard method for creating a walled cavity
  load comb |tmp
  clk fill tube
  clk dilate
  clk clear tube
  clk latshow 67 67 7
  clk fill

  mode cB
  cradius = 0.1

  clk step 1   % copies the trefoil in the BFACF Engine to the Arena
  
  silent = false
  echo
  echo
  echo "Labyrinth in San Vitale, Ravenna, Italy"
  echo
  
  function 1 "lua . ShowLuaSource ()"
  tfunc \rr[11/16] "echo;echo;echo Press F1 to see Lua source;echo"
]])

Title ("Knot Walks a Labyrinth")

function Walk (z, stepSize, text, callback)
  executeKP ("txt fill on")
  executeKP ("txt c -50 " .. '"' .. text .. '" "lua . ' .. callback .. ' ()"')
  if stepSize < 1 then
    return
  end
  executeKP ("clk z " .. z)
  executeKP ("clk run " .. stepSize)
end

function WalkNow ()
  Walk (1, 5000, "walk faster!", "WalkFaster")
end

function WalkFaster ()
  Walk (1, 15000, "walk super fast!", "WalkSuperFast")
end

function WalkSuperFast ()
  Walk (1, 1000000, "unwalk", "UnWalk")
end

function UnWalk ()
  Walk (0.18, 20000, "walk now", "WalkNow")
end

Walk (0.18, 0, "walk now", "WalkNow")
  


