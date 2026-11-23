--[[

rob scharein
Tuesday, 23-Jan-24 18:43:03 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  Demo ()
  --Title ("surf")
  
  BotButton ("new knot", "lua . Surf1()")

end   -- end of init block

ButtonHelp ()
ButtonStack ("toggle:,fullscreen,fullscreen toggle")
ButtonStack ("select on,phantom sl|draw mode:,s,mode s,sl,mode sl")
ButtonAutoHide (5,7)

function LoadKnot (beadlimit)
  repeat
    executeKP ([[
      silent = true
      if \rr10 < 4 then "knot special" else "knot cd"
      silent = false
    ]])
  until (paramKP ("nbeads") < beadlimit)
end

function SurfInit ()
  executeKP ([[
    delete all
    untran
    surface init
    idle
    go 0
    vcn = 0
    line smooth
    velforce = on
    force 1
  ]])
end


function Surf1 ()
  SurfInit ()
  LoadKnot (1022)
  
  executeKP ([[
    vcn = \ri[3/12]
    vcA = \rr[.5/2]
    sradius = \rr[.1/.8]
    %surface radf arc vcn mul vcphi add T \rr{3/16} mul add cos vcA mul \rr[.1/1] add clamp cyl mul
    surface radf arc vcn mul vcphi add T \rr{1/5} mul add cos vcA mul \rr[.1/1] add clamp cyl mul
    go
    background = black

    hstart=\rr360
  
  ]])
end

Surf1 ()
executeKP ("txt click s")

--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
