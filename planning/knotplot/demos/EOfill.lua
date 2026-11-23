--[[

rob scharein
Sunday, 2024 June 23, 21:36:54 PDT

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    ortho
    vscale = 0.207152
    sradius = 0.259580
    mode sE
    background = black
    new = false
    stusplit = 1
    until once yes
    alias -e col "lua . SetColours('$0','$1','$2')"
    alias -e eoload "lua . EOload ('$0')"
  ]])

  Demo ()
  Title ("Even / Odd filling")
  SubTitle ("orthographic projection")

  firstcall = true
  relaxing = false

  BotButton ("rerun demo", 'lua rerun')
ShowSourceButton ()

ButtonHelp ()

ButtonStack ("toggle:"
        --..  ",draw mode,lua . ToggleDrawingMode ()"
        --..  ",xy-plane,show ~grid ~axes"
        ..  ",relaxing,lua . ToggleRelaxing ()"
        ..  ",fullscreen,fullscreen toggle"
            )
ButtonStack ("select on,group draw|draw:"
        ..   ",E,mode E"
        ..   ",sE,mode sE"
        ..   ",cbE,mode cbE"
        )
        
extraItem = ""
if isme () then
  extraItem = ",newcd,lua . createWithNcomps ('knot newcd');fitto 17"
end

ButtonStack ("load:"
         ..  ",cat,lua . NewKnot (1)"
         ..  ",CD,lua . NewKnot (2)"
         ..  ",both,lua . NewKnot ()"
         ..  ",spec,lua . LoadSpecialCollectionKnot ()"
         ..  extraItem
              )
ButtonStack ("action:"
         ..  ",rotate,lua . rotate ()"
         ..  ",random,lua . rcols()"
            )
           
ButtonStack ("left")
executeKP ('txt push;txt fill off;txt 15 .01 " ";txt pop')

ButtonStack ("select on,group background|background:"
        .. ",black,background=black"
        .. ",grey,background=KnotPlotGrey"
        .. ",white,background=white"
        .. ",random,lua . RandomColour(3)"
        )

ButtonStack ("select on,group fill|fill:"
        .. ",red,lua . SetFill ('red')"
        .. ",blue,lua . SetFill ('blue')"
        .. ",green,lua . SetFill('green')"
        .. ",dorange,lua . SetFill ('darkorange')"
        .. ",black,lua . SetFill ('black')"
        .. ",white,lua . SetFill ('white')"
        .. ",random,lua . RandomColour(2)"
        )

ButtonStack ("select on,group knot|knot:"
        .. ",red,lua . SetKnot('red')"
        .. ",blue,lua . SetKnot('blue')"
        .. ",green,lua . SetKnot('green')"
        .. ",orange,lua . SetKnot('KnotPlotOrange')"
        .. ",black,lua . SetKnot ('black')"
        .. ",white,lua . SetKnot ('white')"
        .. ",random,lua . RandomColour(1)"
        )


ButtonStack ("select on,group winding|winding rule:"
         ..  ",odd,tess 0"
         ..  ",non0,tess 1"
         ..  ",pos,tess 2"
         ..  ",neg,tess 3"
         ..  ",a>=2,tess 4"
            )
            
end   -- end of init block

function rcols ()
  local wind = chooseKP ("odd non0 pos neg a>=2", "10 4 2 2 1"  )
  local method = chooseKP ("A,B", "10,1")
  local knot = chooseKP ("red blue green orange random black white", "1 1 1 4 4 1 1")
  local fill = chooseKP ("red blue green dorange random black white", "1 5 1 1 5 1 1")
  local back = chooseKP ("black grey white random", "9 1 1 1")
  local mode = chooseKP ("E sE cbE", "1 14 2")
  local load = chooseKP ("cat CD both spec", "1 1 1 1")
  
  executeKP (wind, method, knot, fill, back, mode, load, [[
    txt click ARG1
    %txt click ARG2
    txt click ARG3 knot
    txt click ARG4 fill
    txt click ARG5 background
    txt click ARG6
    txt click ARG7
  ]])
end

idlecommand = nil

function rotate (com)
  if com then
    idlecommand = com
  else
   idlecommand = "about " .. chooseKP ("x y") .. ' ' .. Random ("rr+-.3")
  end
  
  executeKP (idlecommand, [[
    idle "ARG1"
  ]])
end


function ToggleRelaxing ()
  idlecommand = nil
  relaxing = not relaxing
  if relaxing then
    executeKP ("go")
  else
    executeKP ("go 0")
  end
end

function RandomColour (which)
  local com = captureKP ("colour choose random")
  if which == 1 then
    com = "colour all " .. com
  elseif which == 2 then
    com = "tess colour " .. com
  else
    com = "background = " .. com
  end
  
  executeKP (com, [[
    echo
    echo ARG1
    ARG1
  ]])
end


function SetFill (colour)
  executeKP (colour, [[
    echo tess colour ARG1
    tess colour ARG1
    display true
  ]])
end

knotcolour = "not set"
-- should do the same for the other colours

function SetKnot (colour)
  knotcolour = colour
  executeKP (knotcolour, [[
    echo colour all ARG1
    colour all ARG1
    display true
  ]])
end

function SetColours (kc, fc, bc)
  knotcolour = kc
  executeKP (knotcolour, fc, bc, [[
    colour all ARG1
    tess colour ARG2
    background = ARG3
  ]])
end



function LoadSpecialCollectionKnot ()
  --[[
  
    DoUntil uses the idle function
    so we have to work around that
    
  --]]
  
  local wasrelaxing = relaxing
  
  local function load ()
    executeKP ([[
      #10 echo
      knot spec
    ]])
  end
  
  local function check ()
    --if tonumber (paramKP ('ncomp')) ~= 1 then
    --  return false
    --end
    if tonumber (captureKP ("xing")) > 155 then
      return false
    end
    local c = lcaptureKP ("open")

    if c [4] ~= "closed." then
      return false
    end

    return true
  end
  
  local function success (a, b, c)
    executeKP ([[
      silent = false
      Drawing = true
    ]])

    EOload (captureKP ("util last"))  -- last knot loaded
    
    if wasrelaxing then
      relaxing = false
      ToggleRelaxing ()
    end
    
    if idlecommand then
      rotate (idlecommand)
    end
    
  end
  
  echoKP ("\n\n\n\n")
  executeKP ([[
    silent = true  % this doesn't seem to work!!
    Drawing = false
  ]])
  
  DoUntil (load, check, 0, success)
end

kpcom = {'knot 1',                   -- load a knot from the catalogue with 1 component
         'until Ncomp 1 "knot cd"'}  -- keep loading cd knots until get one with 1 component

function NewKnot (which)
  if which == nil then
    which = RollDie (2)
  end

  local com = kpcom [which]
  if FlipCoin () then
    com =  string.gsub (com, "cd", "newcd")
  end
  executeKP (com, [[
    ARG1
    fitto 17
  ]])
end

UI.orthoMouse (function ()
                 SubTitle ("perspective projection")
               end,
               function ()
                 SubTitle ("orthographic projection")
                end
               )


function tess ()
  for i = 0, 4 do
    executeKP (i, [[
      tess ARG1
      lximgout tARG1 4
    ]])
  end
end     

NewKnot ()

--if firstcall then

  cols = chooseKP ("orange blue,red green,green red", "11,1,1")
  --print ("cols is " .. cols)
  col = explode (" ", cols)
  back = chooseKP ("black white grey", "30 3 1")
  executeKP (col [1], col [2], back, [[
    echo ARG1
    %silent = true
    txt click sE
    txt click ARG3 background
    txt click ARG2 fill
    echo txt click ARG1  knot
    txt click ARG1  knot
    txt click odd
    silent = false
  ]])
  firstcall = false
--end


requireKPbuild (5081)  -- for newcd knots (5069), txt groups as strings (5072), createWithNcomps, isme (5081)

--[[

BEGIN HELP

This demo shows how to construct a Even / Odd colouring of a knot,
often called a `checkerboard colouring'.

How to work it:
  -- first load a new knot by clicking one of the load buttons.
     The `cat' button randomly chooses a knot from the standard
     catalogue (the Rolfsen knots) whereas the `CD' button randomly
     selects a one component knot the catalogue of CD knots with
     nice symmetries. To choose from both use the `both' button.
     The `spec' button loads from the KnotPlot Special Collection.
     
     If you know the name of a knot you'd like to see EO filled,
     just load it as usual
     
       load haken.k
       load 13nh_463
     
  -- you can change the knot, fill and background colours
     by using the button stacks on the left side of the Arena.
     you can also use the `col' alias to set all three at once:
     
       col red green blue
       col grey pink blue
       
     for example
    
  -- default drawing mode is equivalent to the KnotPlot command
     `mode sE' (smooth tubes and EO-fill), two other options are
     available.
     
Knots are viewed in an orthographic projection by default, as the
EO fill looks better in this mode because the EO fill lines up with
the knot outline. Use the mouse to rotate the view and you'll see
what is happening behind the scenes.
  
Fun stuff:
`random' button in the `action:' button stack randomizes pretty much
everything that can be randomized. Some combinations are interesting
but many are duds. Click often!


END HELP


ideas:

instead of instant change between ortho and persp, have a smooth change

--]]
