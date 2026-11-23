--[[

Create an initial random embedding, then relax until the knot reaches a
a "safe" embedding.  This example uses a coroutine that yields execution
to KnotPlot.  The KnotPlot user can rotate or scale the view whilst the
relaxation is taking place, or do any other action.  Without the coroutine
KnotPlot would be "frozen" until the desired condition is achieved.

--]]

Demo ()

-- send a block of commands to KnotPlot
executeKP ([[
  reset all
  cyl-rad = 0.2
  silent = true
  random uniform 333
  coll allow
  silent = false
  txt clobber on
]])

BotTitle ("relaxing until safe")


function relax ()
  executeKP ("ago 11")
end

function ReportStuff (theTimeTaken, numberSteps, didTimeOut)
  if didTimeOut then
    status = "FAILED!!!!"
  else
    status = "done!"
  end
  BotTitle (status .. " took " .. string.format ("%.2f", theTimeTaken) .. " seconds, steps " ..
             numberSteps)
  executeKP ("safe")
end

function Never ()
  return false
end

DoUntil (relax, Safe, 12, ReportStuff)

  
ShowSourceButton ()
