Demo ()
require "Vector3"
  

moviesLoaded = captureKP ("movie clist")

if moviesLoaded ~= "perko1 perko2" then
  isReady = true
  executeKP ([[
    reset all
    vscale = 0.21
    sradius = 0.69
    grsize = 44
    
    silent = true
    movie load Perko1.kpm perko1
    movie load Perko2.kpm perko2

    movie time perko1 5
    movie time perko2 1.6

    movie atend perko1 "lua . Finish1 ()"
    movie atend perko2 "lua . Finish2 ()"

    movie tween perko1 yes
    movie tween perko2 yes
    
    function 2 "www knotplot.com/perko"
    function 3 "www en.wikipedia.org/wiki/Perko_pair"
  ]])
  
end

executeKP ([[
    background = "KnotPlot Blue"
    display true
    auto = false
    hstart = 200
    saturation = 0.7
    hincr = 0
    ncur=2
    nseg=9
    load PerkoAB.k
    silent = false
    txt init
    txt fcolour "Royal Blue" .7
    txt centre
    txt font 3
    txt fill on
    txt c 30 "click to see equivalence" "lua . Start()"
    txt on
    
    #3 echo
    echo "Note: for this demo, writhes are computed using an"
    echo "      orthographic projection to the xy-plane"
    echo
]])

Title ("The Perko Pair")

function CountPlusMinus (gc)
  local kount = 0
  for c in string.gmatch (gc, ".") do
    if c == "+" then
      kount = kount + 1
    elseif c == "-" then
      kount = kount - 1
    end
  end
  return kount
end

function Writhe ()
  -- invalid if components cross each other
  egc = captureKP ("gauss")
  code = explode ("|", egc)
  writheA = string.format ("%.0f", CountPlusMinus (code [1]) / 2)
  writheB = string.format ("%.0f", CountPlusMinus (code [2]) / 2)
  -- return writheA, writheB
end

function Start ()
  executeKP ([[
    txt delete click
    txt fill off
    txt c 30 "you can rotate / scale the view with the mouse during the animation"
    tfunction .02 "lua . ShowWrithes (true, true)" 0 rep .05
    movie play perko1
  ]])
end

function Finish1 ()

  executeKP ([[
    silent = true
    tfunc reset
    movie play perko2
    tfunction .02 "lua . ShowWrithes (false, true)" 0 rep .05
    silent = false
  ]])
  
  Writhe ()
  
end

function Finish2 ()
  executeKP ([[
  txt delete you
  silent = true
  tfunc reset
  silent = false
  txt font 3
  txt centre
  #2 txt delete writhe
  keep 0
  lua . ShowWrithes (false, false)
  
  txt fill on
  txt lineskip -26

  txt c 30 "run again" "lua run Perko"
  txt fill off
  txt c a "rotate or scale the view and run this demo again"
  txt c a " "
  txt fill on
  txt c a "visit the Perko page at the KnotPlot Site" "www knotplot.com/perko"
  txt fill off
  txt c a "for more information on the Perko knots, click the button below:"
  txt on
  ]])
end

function AddLabel (position, text)
  executeKP (position.x, position.y, 0.0, text, [[
  txt push
  txt centre
  txt fill off
  txt font 4
  txt ARG1 ARG2 ARG3 "ARG4"
  txt pop
  ]])
end

function ShowWrithes (compute, doB)
  if compute then Writhe () end

  -- we could position the text explicitly, but it's interesting
  -- to see how the position can be calculated

  stuff = mlcaptureKP ("info -full m")  -- get the centres of mass
  cofmA = Vector3.new (stuff [1][1], stuff [1][2], stuff [1][3])
  if doB then cofmB = Vector3.new (stuff [2][1], stuff [2][2], stuff [2][3]) end
  --print (Vector3.tostring (cofmA))
  --print (Vector3.tostring (cofmB))

  offset = Vector3.new (0, -12, 0)
  locA = Vector3.add (cofmA, offset)
  if doB then locB = Vector3.add (cofmB, offset) end

  executeKP ("#2 txt delete writhe")
  AddLabel (locA, "writhe = " .. writheA)
  if doB then AddLabel (locB, "writhe = " .. writheB) end
end

ShowWrithes (true, true)

ShowSourceButton ()

PrintArgs ()


ButtonHelp ()
ButtonStack ('toggle:'
          .. ',axes,show ~axes'
          .. ',xy-plane,show ~grid'
          .. ',draw mode,lua . ToggleDrawingMode()'
          .. ',fullscreen,full toggle'
            )
ButtonStack ('select on,group 109|rotate:'
          --.. ',x up,rotate yz'
          .. ',y up,rotate xy'
          .. ',z up,rotate xz'
          )
          
          
executeKP ([[
  txt click "y up"
]])

--[[

BEGIN HELP

These are the famous Perko pair knots, listed as distinct
knots in many knot tables since the 19th century, until
Kenneth Perko showed in 1974 that they were the same knot.
He proved the equivalence by showing a sequence of diagrams
leading from one to the other.

The animation in this demo is a different demonstration of the
same fact, obtained by relaxing the two knots using KnotPlot.
That relaxation, together with rigid rotations is all that is
needed to prove the equivalence.

Press F2 to visit the Perko pair page at the KnotPlot Site

Press F3 to go to the Perko pair page on Wikipedia

ON THE CLASSIFICATION OF KNOTS,
Kenneth A. Perko, Jr.
Proceedings of the American Mathematical Society,
Vol. 45, No. 2. (Aug., 1974), pp. 262-266.

END HELP

--]]
