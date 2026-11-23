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

BotTitle ("relaxing until thicker than " .. desiredThickness .. " using a coroutine")

startTime = timeKP ()

co = coroutine.create (
function ()
  repeat
    executeKP ("ago 3")    -- this command should not take too long to complete
    thickness = Thickness ()
    Title ("thickness is " .. string.format ("%.3f", thickness))
    coroutine.yield ()
  until (thickness > desiredThickness)
end
)

startTime = timeKP ()

function step ()
  if coroutine.status (co) == "dead" then
    executeKP ("idle")
    endTime = timeKP ()
    BotTitle ("done! " .. " the thickness is now " .. string.format ("%.3f", Thickness()) ..
        ", took " .. string.format ("%.2f", endTime - startTime) .. " seconds")
  else
    coroutine.resume (co)
  end
end


executeKP ('idle "lua . step ()"')


ShowSourceButton ()
