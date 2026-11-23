--[[

rob scharein
Monday, 01-Jan-24 18:34:35 UTC

An example of how to return output of an arbitrary command line program.
In this case it's my `remind' utility that returns info about my reminders.

To be useful to you, change `remind' to the command program of interest and
make any other changes you need to get the data you want. 

--]]

function NextReminder ()
  --[[
    returns the next reminder and the number of seconds until it happens
    `remind' command line programme returns text of the form:
       next reminder is |golden light| with notes |sun info| in 26.857 minutes
  --]]
  
  local rem = osx ("remind -i | grep next")
  local info = explode (" ", rem)
  local seconds = info [#info - 1]
  if info [#info] == "hours" then
    seconds =  seconds * 60.0 * 60
  elseif info [#info] == "minutes" then
    seconds = seconds * 60.0
  end

  info = explode ("|", rem)
  return info [2], seconds
end


  


