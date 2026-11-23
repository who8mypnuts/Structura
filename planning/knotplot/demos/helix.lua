Demo ()

executeKP ([[
  reset all
  sradius = 0.14
  rotate x -65
  alias ~helix "lua . Helix ()"
  txt clobber on
  txt font 3
  txt left
  txt fill on
  txt 15 15 run "lua . RunStop ()"
  txt fill off
  txt centre
  txt font 4
  #3 echo
  echo click the `run' button in the lower left
  echo to create helices continuously
  echo -f
]])


BotButton ("new helix", "~helix;lua . StopIfRunning ()")

if demo ~= luaSource then  -- note: this block of code is executed only
  demo = luaSource
  call = 1                 --       the first time helix.lua is run if
  nbeads_old = 80          --       there is a sequence of consecutive
  inradius_old = 20        --       runs.  This is done by checking the
  outradius_old = 20.1     --       value of the demo variable.
  rise_old = 0             --       When this script is run the second
  nturns_old = 1           --       time, this block is not run because
  running = false          --       not running continuously
  hstart = 33
end

-- print ("helix call #" .. call)
call = call + 1


function RunStop ()
  executeKP ([[
    txt push
    txt left
    txt font 3
    txt fill on
  ]])
  
  if running then
    executeKP ("idle")
    executeKP ('txt 15 15 run "lua . RunStop ()')
    running = false
    Explain ()
  else
    executeKP ('idle "lua . Helix ()"')
    executeKP ('txt 15 15 stop "lua . RunStop ()')
    running = true
  end
  
  executeKP ("txt pop")
end

function StopIfRunning ()
  if running then RunStop () end
end

function Helix ()
  startTime = timeKP ()
  duration = Random ("rr[0.1/0.55]")
  nbeads_new = Random ("ri[60/140]")
  inradius_new = Random ("rr+-12")
  outradius_new = Random ("rr+-12")
  rise_new = Random ("rr[0/4]")
  nturns_new = Random ("rr[2/7]")
  executeKP ("silent = false")
  executeKP ("hstart = " .. hstart)
  hstart = hstart + 1
  repeat
    p = (timeKP () - startTime) / duration
    MakeHelix (
      Interpolate (nbeads_old, nbeads_new, p),
      Interpolate (inradius_old, inradius_new, p),
      Interpolate (outradius_old, outradius_new, p),
      Interpolate (rise_old, rise_new, p),
      Interpolate (nturns_old, nturns_new, p))
  until (p > 1.0)
  nbeads_old = nbeads_new
  inradius_old = inradius_new
  outradius_old = outradius_new
  rise_old = rise_new
  nturns_old = nturns_new
end

function MakeHelix (nbeads, inradius, outradius, rise, nturns)
  name = "helix"
     .. " " .. string.format ("%.0f", nbeads)
     .. " " .. string.format ("%.2f", inradius) .. "/" .. string.format ("%.2f", outradius)
     .. " " .. string.format ("%.2f", rise)
     .. " " .. string.format ("%.2f", nturns)
  executeKP (name)
  executeKP ('txt c -20 "' .. name .. '"' )
  executeKP ("display true")
  if not running then
    Explain ()
  end
end

function Explain ()
  executeKP (name, [[
    #3 echo
    echo use this command to create this helix:
    echo ARG1
    meta "created with" "ARG1"
  ]])
end

Helix ()


ShowSourceButton ()

-- add option: idle cmode -1;lua . Helix () with draw spec

