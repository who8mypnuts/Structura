--[[

rob scharein
Tuesday, 02-Apr-24 21:48:53 UTC

--]]

executeKP ([[
  reset all
  txt on
  txt clobber on
  play init
  txt push
  txt group 111
  txt centre
  txt font 4
  txt c c+20 "drag an image onto the view"
  txt c c-20 "and then click the `1' button"
  txt pop
]])

Demo ()
ButtonHelp ()

function Step1 ()
  Title ("step 1")
  SubTitle ("created contours")
  executeKP ([[
    txt delete group 111
    sradius = 0.1
    load _image2KP.tmp
    fitto 22
    reflect y
    scale .4
  ]])
end

function Step2 ()
  Title ("step 2")
  SubTitle ("traced contours and prepared underpasses")
  executeKP ([[
    copy f
    mode n
    copy A
  ]])
end

function Step3 ()
  Title ("step 3")
  SubTitle ("filled underpasses")
  executeKP ([[
    copy t
    mode cb
    join all
    #2 echo

    if safe then "play 87" else "play 47"
    safe
  ]])
end

function Step4 ()
  Title ("step 4")
  SubTitle ("refined to equilateral")
  executeKP ([[
    refine equilateral 1
    ccmode = 2
    #2 echo

    if safe then "play 87" else "play 47"
    safe
  ]])
end

function Step5 ()
  Title ("step 5")
  SubTitle ("relaxing")
  executeKP ([[
    ago 222
    panel draw
    untran
    persp
    mode s
    sradius = 0.4
    centre

    echo
    xing
  ]])
  SubTitle ("relaxed")
end

--Step1 ()


--[[

BEGIN HELP

How to work it:

   --- drag and drop an image of a line drawing of a knot
       into the view area of image2KP

   --- click on the buttons 1, 2, 3, 4 and 5 in succession
   
Step 1 creates a set of contours using routines in OpenCV

Step 2 traces the centre line of each contour and then
prepares the underpasses. You might want to rotate the
view at this point

Step 3 simply joins the underpasses

Step 4 does an equilateral refinement of the knot / link

Step 5 does some relaxation to make things look nice

END HELP

--]]
