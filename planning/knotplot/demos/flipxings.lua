--[[

rob scharein, 29 november 2023

in the Public Domain


first put this file in the same directory as
you start KnotPlot from and then start
KnotPlot from a Terminal window
   
run the script in KnotPlot:
   lua run flipxings
   
pick a knot to create a new template from:
   newtemplate 6.3
which could be one that you created and is in
your working directory
   newtemplate myknot
   
check to make sure there are no errors, in particular
the "*** too few edges!" error
   
if things seem OK, then enter commands such as
   flip 0
   flip 5
where the number you pick matches the number seen
in the tangle temmplate.  Any numuber outside
this range will substitute a 1 into every tangle
holder, thereby recreating the original knot type.

--]]

executeKP ([[
  reset all
  
  % the name of the following aliases should be different from
  % any KnotPlot command
  
  alias newtemplate "lua . NewTemplate ($0)"
  alias flip "lua . FlipCrossing ($0)"
  
  sradius = 0.3
  
  echo
  echo newtemplate KNOT-FILE
  echo flip THOLDER_INDEX
]])

numberCrossings = 0

function NewTemplate (knotName)
  executeKP (knotName, [[
    load ARG1
  ]])
  
  numberCrossings = tonumber (captureKP ("xing"))
  
  executeKP (numberCrossings, [[
    echo number of crossings is ARG1
    template auto
    tholder install
  ]])
end

function FlipCrossing (which)
  tangleCommand = "t"
  for i = 0, numberCrossings - 1 do
    if which == i then
      tangleCommand = "1z" .. tangleCommand
    else
      tangleCommand = "1" .. tangleCommand
    end
  end
  
  executeKP (tangleCommand, [[
    echo tangle ARG1
    tangle ARG1
    
    % do a little bit of relaxation to smooth things out
    ago 66
    centre
  ]])

end


  
  
