--[[

Example of how to get some information from KnotPlot and to make a
decision based on that information.  Display the information as text.

The same information is displayed in the KnotPlot Command Window using
traditional methods. 

--]]

if demo ~= luaSource then
  Demo ()
  RequireKLE (6)
  executeKP ("reset all")
  demo = luaSource
  ShowSourceButton ()
end


-- we want to avoid 0.2.1, 0.3.1 and 0.4.1 (knot numbers 251, 343 and 379)
-- since those have no crossings and get mis-identified as 0.1
-- choose one of four ranges with different relative probabilities
indexRange = chooseKP ("\\ri[1/250] \\ri[252/342] \\ri[344/378] \\ri[380/383]",
                       "250 91 35 4")


-- print ("knot number " .. indexRange)
executeKP ("knot number " .. indexRange)

executeKP ([[
  txt delete all
  txt clobber on
  tfunc reset
  idle
  swap random
  <randorient.kps
  txt centre
  txt font 4
  info
  acn
  thickness
  gauss
  homfly    % can also use homfly-pt or flypmoth
  sradius = 0.34
  cradius = 0.12
  id
]])

-- choose mode s with 7 times the probability of mode cb
executeKP ("mode " .. chooseKP ("cb,s", "1,7"))

something = "knot"
separator = ": "

function addText (label, value)
  executeKP ('txt c a "' .. label .. separator .. value .. '"')
end

function addText2 (label)
  executeKP (label, 'txt c a "ARG1"')
end

info = tcaptureKP ("info s")
if tonumber (info [0]) > 1 then
  something = "link"
end
Title ("get some information about a " .. something)

addText2 (Plural (tonumber (info [0]), "component") .. ", " .. Plural (info [1], "bead"))

addText ("extent in x", info [5] .. " <---> " .. info [6])
addText ("extent in y", info [7] .. " <---> " .. info [8])
addText ("extent in z", info [9] .. " <---> " .. info [10])
addText ("centre of mass", "(" .. info [11] .. ", " .. info [12] .. ", " .. info [13] .. ")")
addText ("radius", info [14])
addText ("volume", info [15])

stuff = tcaptureKP ("acn")
addText ("average crossing number", stuff [4])
addText ("space writhe", stuff [9])
addText ("thickness", Thickness ())

gc = captureKP ("gauss")     -- captureKP captures only the first line of output
homfly = captureKP ("homfly")
knotID = captureKP ("id")

-- split long homflys into multiple lines
homflyLine = mlcaptureKP ('explode " + " "' .. homfly .. '" 45')

-- randomly choose between HOMFLY-PT, HOMFLY and FLYPMOTH
--                      names                        relative probability
homflyName = chooseKP ("HOMFLY-PT HOMFLYPT HOMFLY FLYPMOTH", "6 6 2 7")

if tonumber (info [0]) == 1 then
  dc = captureKP ("dowker")
  addText ("dowker code", dc)
end
addText ('gauss code', gc)

for i = 1, #homflyLine do
  line = homflyLine [i]
  out = ""
  for j = 1, #line do
    out = out .. line [j] .. " "
  end
  addText (homflyName, out)
  separator = ""
  homflyName = ""
end

separator = ": "

addText (something .. " ID", knotID)

BotTitle ("compare to the same info in the Command Window")


-- just for fun things are below

executeKP ('tfunction \\rr[22/44] "lua . Fun ()"')

function Fun ()
  -- cut along one of planes x=0, y=0 or z=0
  -- and then cut into pieces
  
  executeKP (chooseKP ("x y z"), Random ("ri[5/16]"), [[
    echo
    cut span ARG1 0
    echo cut along plane ARG1=0
    cut pieces ARG2
    echo cut into ARG2 pieces
    
    txt init
    revbeads random
    tanforce = on
    tanmag = 0.05
    idle "ago 1;fitto sphere 8"
    coll a
    velf = true
    force 1
    tfunc 18 "revbeads;jitter 1" 0 rep 14 29
  ]])
end

