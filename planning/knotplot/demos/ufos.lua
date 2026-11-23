--[[

rob scharein
Tuesday, 23-Jan-24 21:23:48 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    background = black
    collision allow
    silent = true
    
    tg1off = \rr[2/6]

    dstep = 1
    hstart=\rr360
    auto-colour=off
    hincr=\rr[20/180]
    saturation = \rr[.7/1.0]
    ncur=\ri[3/4]
    nseg=14
    sradius = \rr[.3/.5]
    force 1
    velforce = on
    vcA =\ rr[.2/.9]
    %if \rr1 < .8 then "mathsv s \rr55 1 \rr1 e"
    if \rr1 < .05 then "vcn=\ri[1/5]"
    velmag=\rr[.05/.1]

    glop backface f

    %alias -e unk "unknot 9 2 \rr+-3 \rr+-3 \rr+-3 rand"

    new = false
    
    
    ascale = .02
    fscale=39

    %if \rr1 < .01 then "spec;tex SphereMap;texture mode modu;sat=\rr.5;cyl=1"
    %if \rr1 < .01 then "spec;tex SphereMap;texture mode replace;sat=\rr.5;cyl=1"
    %if \rr9 < 1 then "read electric.kps;ncur=4;spec"
    %if \rr9 < 1 then "<fun-with-accbuff.kps"

    if \rr2 < 1 then "fixcofm=t" else "fixcofm=f"
    tanforce = on

    surface radf arc vcn mul vcphi add csquare vcA mul 1 add cyl mul
    vcn=\ri[2/5]
    vcphi = \rr6.28
    vcA = \rr[.4/.9]

    go
    silent = false

  ]])

  Demo ()
  Title ("UFOs!")
  

end   -- end of init block

ButtonHelp ()
ButtonStack ("toggle:,motion blur,lua . ToggleMotionBlur(),fullscreen,fullscreen toggle")
ButtonStack ("saucers:,add,lua . NewSaucer(),swirl,lua . Swirl(),delete,delete all")


stack = "select on,group 102,phantom none|fps limit:"
fps = 132
for i = 1, 6 do
  stack = stack .. "," .. fps .. ",lua . Go(" .. fps .. ")"
  fps = fps + 72
end
--print (stack)
ButtonStack (stack .. ",none,lua . Go(0)")

ButtonAutoHide (5,7)

function ToggleMotionBlur ()
  executeKP ([[
    if accbuffon then "accbuff off" else "accbuff decay 0.980730;accbuff accum 0.217651;accbuff return 0.225359;back=#000;accbuff on;accbuff clear"
  ]])
end

function Swirl ()
  executeKP ([[
    swirl \rr[-111/111]
  ]])
end

function Open ()
  executeKP ([[
    open all
    ago 123
    close all
    txt click 420
  ]])
end

function Go (value)
  if value == 0 then
    executeKP ([[
      echo frame speed limiting off
      go
    ]])
  else
    executeKP (value, [[
      echo frame speed limited to ARG1
      go inf limit ARG1
    ]])
  end
end

function NewSaucer ()
  executeKP (Random ("rr[0/360]"), Random ("rr[.6/1]"), Random ("rr[.6/1]"), [[
    silent = true
    unknot \ri[8/11] \rr[2/3] \rr+-3 \rr+-3 \rr+-3 rand
    %colour last random
    echo colour last hsv:ARG1/ARG2/ARG3
    colour last hsv:ARG1/ARG2/ARG3
    silent = false
  ]])
end

executeKP ([[
  txt click 420
  #2 lua . NewSaucer ()
  project r
  centre

  <randorient.kps
  if \rr1 < .5 then "refl rr" else "refl r"
  %if \rr1 < .01 then "draw spec"
  %if \rr1 < .4 then "scale \rr[.5/2] \rr[.5/2] \rr[.5/2]"

  %if \rr11 < 1 then "mode cBf;cyl=0.18;bead=0.3"
]])

--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
