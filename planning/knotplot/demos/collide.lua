--[[

rob scharein
Tuesday, 23-Jan-24 03:13:59 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  Demo ()
  Title ("Collide Knots")

end   -- end of init block

ButtonHelp ()
ButtonStack ('toggle:,fullscreen,full toggle')
ButtonStack ("left")
ButtonStack ("select on,phantom AA|collide:,"
              .. "A,lua . CollideA(),"
              .. "B,lua . CollideB(),"
              .. "C,lua . CollideC(),"
              .. "D,lua . CollideD(),"
              .. "E,lua . CollideE()"
            )
            
function CollideInit ()
  executeKP ([[
    delete all
    tfunction reset
    tanforce = off
    surface init
    velforce = off
    vcn = 0
  ]])
end

function CollideA()
  CollideInit ()
  executeKP ([[
    verbose = 0
    silent = true
    
    alias -e velrad "velocity rad \rr[-.1/-1]"
    alias -e dupt   "duplicate;translate 6 0 0 last"

    unknot \ri[6/18] 4

    persp 60 .2 120
    reflect r

    Draw = false
    ago 22
    Draw = true

    vscale = 0.21

    translate 30 0 0
    #3 duplicate;about z 90 0;about z -90

    ago 1

    force 1
    velmag = 0.001
    velforce = on

    velrad
    go

    tfunc 3 velrad 0 rep 1 3

    mathsv b 0 0 1 d
    bradius = 1

    %if \rr22 < 1 then "mode B;texture env lupin;texture on"

    surface radf arc vcn mul vcphi add csquare vcA mul 1 add cyl mul
    vcn=\ri6
    vcphi = \rr6.28
    vcA = \rr[.4/.9]

    silent = false
  ]])
end

function CollideB()
  CollideInit ()
  executeKP ([[
    hstart = \rr360
    velforce = false
    force 2
    verbose = false
    silent = true
    vscale = 0.22
    
    Draw = false
    

  ]])
end

function CollideC()
end

function CollideD()
end

function CollideE()
end





--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
