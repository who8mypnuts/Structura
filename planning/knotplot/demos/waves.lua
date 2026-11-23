--[[

rob scharein
Saturday, 20-Jan-24 18:04:05 UTC

A demo of some odd things that can be done with the "wavefront" command.

Reworking of the ancient `waves' demo written in KPS.


--]]

--if demo ~= nil then print ("demo is " .. demo) end
--if luaSource ~= nil then print ("luaSource is " .. luaSource) end

if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    %txt scolour #000
    %txt sfcolour #fb0 .8
    alias -e bg "lua . Background ('$0')"
    alias -e wc "lua . WaveColour ('$0')"
    unknot
  ]])

  Demo ()


  ButtonHelp ()
  ButtonStack ("toggle:,blending,lua . ToggleBlending(),motion blur,lua . ToggleMotionBlur(),fullscreen,fullscreen toggle")
  ButtonStack ("select on,group 108,phantom wbc|mode:,w,lua . SetMode('w'),wb,lua . SetMode('wb'),wbc,lua . SetMode('wbc')")
  ButtonStack ("select on,group 102,phantom none|fps limit:,30,lua . Go(30),60,lua . Go(60),90,lua . Go(90),none,lua . Go(0)")
  ButtonStack ("select on,group 109,phantom dorange|background:"
     .. ",black,lua . Background ('black')"
     .. ",white,lua . Background ('white')"
     .. ",blue,lua . Background ('blue')"
     .. ",dorange,lua . Background ('dorange')"
           )
  ButtonStack ("select on,group 111,phantom dorange|wave colour:"
     .. ",black,lua . WaveColour ('black')"
     .. ",white,lua . WaveColour ('white')"
     .. ",blue,lua . WaveColour ('blue')"
     .. ",dorange,lua . WaveColour ('dorange')"
           )
           
  ButtonStack ("left")

  executeKP ('txt push;txt fill off;txt 15 .01 " ";txt pop')

  ButtonStack ("select on,group 1022|select a demo:"
      .. ",wave 1,lua . Demo1()"
      .. ",wave 2,lua . Demo2()"
      .. ",wave 3,lua . Demo3()"
      .. ",wave 4,lua . Demo4()"
      .. ",wave 5,lua . Demo5()"
      .. ",wave 6,lua . Demo6()"
            )


  ButtonAutoHide (5,8)
  
  blending = false
  showextrainfo = false

end   -- end of init block

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


function ToggleBlending ()
  if blending then
    executeKP ("blend sa msa")
  else
    executeKP ("blend one one")
  end
  blending = not blending
end

function SetMode (mode)
  executeKP ("mode " .. mode)
end


function ColourInfo (what, which, colour)
  if not showextrainfo then return end
  executeKP (what, which, colour, [[
    echo
    echo to set the ARG1 colour use the command:
    echo ARG2 ARG3
    echo replacing `ARG3' with any other colour name
  ]])
end

function Background (colour)
  ColourInfo ("background", "bg", colour)
  executeKP (colour, [[
    background = ARG1
  ]])
end

function WaveColour (colour)
  ColourInfo ("wave", "wc", colour)
  executeKP (Colour (colour), [[
    cmode 0
    wave mode 0
    wave rgb ARG1
  ]])
end

function WavesInit ()
  executeKP ([[
    verbose = false
    sradius = .06
    cradius = .06

    trx = 0
    try = 0
    trz = 0
    vscale = 0.35
    N-torus = 80
    tfunc reset
    force 2
    coll f
    wavefront rotate 1
    wavefront nsegments 102 90.000000
    wavefront start 0
    wavefront skip 1
    wavefront c 5.000000
    wavefront nwaves 0
    delete all
    untran
    idle
    ago 1
    rmass off
    spec
    %blend sa msa
    %zbuff t
  ]])
end

function Demo1 ()
  --print ("demo 1")
  WavesInit ()
  executeKP ([[
    silent = true
    sradius = .06
    cradius = .06
    trx = -2.528603
    try = -0.020898
    trz = 0.000000
    vscale = 0.311814

    wavefront nwaves 222
    wavefront c \rr[2.5/4]
    N-torus = \ri[35/90]

    wavefront skip \pN-torus

    vscale = \rr[.3/.38]

    verbose = false

    tfunction 2 "coll a;force 1"

    torus 2 3
    silent = false

    txt click 30
  ]])
end

function Demo2 ()
  --print ("demo 2")
  WavesInit ()
  executeKP ([[
    silent = true

    cradius=.06
    sradius = 0.06
    vscale = 0.15
    trx = -3

    wavefront nwaves 222
    wavefront c \rr[2/7]
    wavefront skip 80
    wavefront init

    vscale = 0.298422
  
    verbose = false

    coll a
    force 1

    unknot
    silent = false

    txt click 30

  ]])

end

function Demo3 ()
  --print ("demo 3")
  WavesInit ()
  
  executeKP ([[

    silent = true

    wavefront start 0
    if \rr2 < 1 then "wavefront skip 8" else "wavefront skip 1"

    wavefront c \rr[2/5]
    wavefront nwaves 240
    force 1
    coll a
    unknot 80
    about z 90
    if \rr2 < 1 then revb
    <randorient.kps
    silent = false

    txt click 30
  ]])
end

function Demo4 ()
  --print ("demo 4")
  WavesInit ()
  
  executeKP ([[
    silent = true
    vscale=\rr[.23/.45]

    sradius=.06
    cradius=.06
    N-torus = \ri[10/20]
    line num \pN-torus
    line
    jitter 9999
    fitto 5
    translate to 0 0 0
    coll a
    force 1
    revbeads
    rmass open
    rmass 0 1
    
    wavefront skip \pN-torus
    wavefront nwaves 222
    wavefront c \rr[2/7]
    wavefront init

    verbose = false

    %tfunc 2 "coll a;force 1"
    coll a
    force 1

    silent = false

    txt click 30
  ]])
end

function Demo5 ()
  --print ("demo 5")
  WavesInit ()
  
  executeKP ([[
    silent = true
    vscale = \rr[.33/.65]
     
    line dir 1 0 0
    line numb 13
    line
    centre
    coll a
    force 1
    rmass open
    jitter .1
    if \rr2 < 1 then "about z 90"
    if \rr2 < 1 then "about y 90"
    <randorient.kps
    wavefront skip 13
    wavefront start 6
    wavefront nwaves 222
    wavefront c \rr[2/7]
    wavefront nseg \ri[3/10] \rr360
    wavefront init
    
    verbose = false

    %tfunc 2 "coll a;force 1"
    coll a
    force 1

    silent = false
    txt click wbc
    txt click 30
  ]])
end

function Demo6 ()
  --print ("demo 6")
  WavesInit ()
  
  executeKP ([[
    silent = true

    N-torus = \ri[20/77]
    unknot

    if \rr7 < 1 then "shift \ri999"

    about y 90
    if \rr2 < 1 then "about x 90"
    sradius=.06
    cradius=.06
    wavefront skip \pN-torus

    coll a
    force 1
    wavefront nwaves 222
    wavefront c \rr[2/7]
    wavefront init

    verbose = false

    silent = false
    txt click 30
  ]])
end


function ToggleMotionBlur ()
  executeKP ([[
    if accbuffon then "accbuff off" else "accbuff decay 0.980730;accbuff accum 0.217651;accbuff return 0.225359;back=#000;accbuff on;accbuff clear"
  ]])
end


function Waves ()
  -- this is neat, but not being used
  fun = {Demo1, Demo2, Demo3, Demo4, Demo5, Demo6}
  fun [RollDie (#fun)]()
end

executeKP (RollDie (6), [[
  txt click 30
  txt click w
  txt click black 109
  txt click dorange 111
  txt click "wave ARG1"
]])

ShowSourceButton ()

showextrainfo = true

--[[

ideas: need a darker/lighter option for wave colour


BEGIN HELP
some helpful text should go here...



some helpful text should go here...

  

some helpful text should go here...

END HELP

--]]
