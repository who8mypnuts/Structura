--[[

rob scharein
Tuesday, 13-Feb-24 22:38:50 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  Demo ()
  Title ("4D Surfaces")
  
  complex = require "complex"
  c = complex

end   -- end of init block

ButtonHelp ()


c.print (c.sqrt (c.new (-1, 0)))

function ProjectivePlane ()
  Title ("4D Projective Plane")
end

function KleinBottle ()
  Title ("4D Klein Bottle")
end

function Usage ()
  echoKP ("Usage:\n  lua run klein|pplane")
end

if #arg ~= 1 then
  Usage ()
else
  if arg [1] == "klein" then
    KleinBottle ()
  elseif arg [1] == "pplane" then
    ProjectivePlane ()
  else
    Usage ()
  end
end


--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
