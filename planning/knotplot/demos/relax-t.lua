--[[

Create an initial random embedding, then relax until the knot reaches a
a desired thickness.  This example uses a coroutine that yields execution
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

desiredThickness = 1.02

BotTitle ("relaxing until thicker than " .. desiredThickness)

function Relax ()
  executeKP ("ago 3")    -- this command should not take too long to complete
end

function CheckThickness ()
  thickness = Thickness ()
  Title ("thickness is " .. string.format ("%.3f", thickness))
  if thickness > desiredThickness then
    return true
  else
    return false
  end
end

function ReportStuff (theTimeTaken, numberSteps, didTimeOut)
  if didTimeOut then
    status = "FAILED!!!!"
  else
    status = "done!"
  end
  BotTitle (status .. " the thickness is now " .. string.format ("%.3f", Thickness()) ..
            ", took " .. string.format ("%.2f", theTimeTaken) .. " seconds, " .. numberSteps .. " steps")
end

-- the following is implemented with a coroutine
DoUntil (Relax, CheckThickness, 33, ReportStuff)

ShowSourceButton ()
