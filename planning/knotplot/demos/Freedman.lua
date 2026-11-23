Demo ()

moviesLoaded = captureKP ("movie clist")

if moviesLoaded ~= "freedman" then
  isReady = true
  executeKP ([[
    reset all
    sradius = 0.2
    vscale = 0.23

    silent = true
    movie load Freedman.kpm freedman
    movie atend freedman "lua . Finish()"
    movie time freedman 5
    silent = false
  ]])
end


executeKP ([[
  drop all 52 35 -20
  if stereo then "back=0" else "spec back"
  txt init
  txt clobber on
  txt centre
  txt font 4
  txt c 108 "Freedman (un)knot"
]])

if FlipCoin () then
  executeKP ('txt c a "Is it a knot or an unknot?"')
else
  executeKP ('txt c a "Is it an unknot or a knot?"')
end
  
executeKP ([[
  txt on
  txt font 3
  txt fill on
  txt c 45 "run animation and find out!" "txt init;movie play freedman"
  hstart = 33
  
  silent = true
  load Freedman.k
  txt on
  Draw = true
  silent = false

  #4 echo " "
  echo This demo rewritten in Lua on 27 March 2022!

  echo " "
  echo -n " The Freedman "
]])
  
if FlipCoin () then
  executeKP ("echo -n knot (or unknot?)")
else
  executeKP ("echo -n unknot (or knot?)")
end
  
executeKP ([[
  echo " (in a form from a paper by Kusner & Sullivan)."
  echo " Click on the button in the view window to run animation. "
  echo " "
]])

executeKP ([[
  go 0   % knot might be relaxing from a previous run
]])

function Finish ()
  executeKP ([[
  refine nbead mult .3
  dstep = 8
  ago 102

  ncur=3
  nseg=12

  dstep=2
  refine nbead mult .5
  ago 102

  dstep=9

  refine nbead mult .5
  go 444
  silent = f

  txt centre
  txt font 4
  txt c 100 "Undone!"

  txt font 3
  txt c 70 "try this: rotate or scale the scene with the mouse before reloading the demo"
  txt fill on
  txt c 45 "reload demo" "lua run Freedman"
  txt c 20 "YouTube movies..." <YouTubeMovies.kps
  txt on

  #3 echo
  echo " *** Try rotating or scaling the scene before reloading the demo"
  echo "     (click and drag left mouse in view window to rotate, right mouse for scale)"
  echo
  ]])
end

ShowSourceButton ()

