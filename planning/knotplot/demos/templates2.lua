--[[

rob scharein, January / February 2023

--]]


Demo ()

-- add code to prevent repeated choices of the same knot

if demo ~= luaSource then    -- this block of code is only executed the first time the
  demo = luaSource           -- templates demo is run (in a sequence of templates runs)
  executeKP ([[
    reset all
    sformat = 1
    itsave = true
    until once true
    alias n "lua . NComponents ($0)"
  ]])
end

executeKP ([[
  sradius = 0.3
  vscale = 0.35
  untran
  delete all
  go 0
  #7 echo
  echo trying to find a knot that creates a
  echo nice tangle template (not all do)
  txt init
  txt on
  txt clobber on
  txt font 3
  txt centre
  txt c -40 "re-run the demo until you get a template you like"
  txt c -60 "then click on the `use template' button below"
]])

function TryOnce ()
  if Random ("rr501") < 242 then
    -- choose one from a number of "special knots"
    specialKnot = chooseKP ("c4/91.k d6/73.k c8/62.k c3/78.k c5/25.k c5/83.k d3/22.k d3/136.k c3/35.k Ash2243.k Ash2360.k Granny.k Square.k Milnor.k Lorenz-xxyxyy.k infinity zero-writhe-tref.k fig8sum.k kawauchi-3.4.2.k buddhist_knot.k goeritz.k K11a363 K11n123 K11n185 L10a40 L10n16 L10n88 L10n97 L11a120 L11a171 L11a412 L11a468 L11a539 L11n204 L11n243 L11n300 L11n309 L11n357 L11n438 10.123 8.18 9.1 9.2 thk-3-10.k")
    output = lcaptureKP ("load " .. specialKnot)
  else
    -- choose something from the basic catalogue, something that has some crossings
    -- this is a lazy way of randomly choosing a knot from the catalogue
    -- whilst avoiding 0.1, 0.2.1, 0.3.1 and 0.4.1
    repeat
      output = lcaptureKP ("knot")
    until (tonumber (captureKP ("xing")) > 0)
  end
  
  -- see if what is chosen makes a suitable tangle template
  executeKP ([[
    centre
    % some knots will produce bad tangle templates using
    % this automatic method. If this happens, one or both
    % of the following commands will set the parameter `panic'
    % to something non-zero (ie, TRUE)
    template auto
    tholder check
  ]])
   
  if paramKP ("panic") == 0 then    -- a panic value of 0 (FALSE) means a good template
    knotName = string.sub (output [#output], 2, -2)    -- strip off the `' from the filename
    Title ("Tangle template made from " .. knotName)
    BotButton ("use template", "lua . UseTemplate ()")
    found = true
  end
end

found = false
startTime = timeKP ()

repeat
  TryOnce ()
  time = timeKP () - startTime
until (found or time > 3)        -- give up after 3 seconds

executeKP ("tholder install;echo")

echoKP ("to re-create this template, enter the following commands:")
echoKP ('load ' .. knotName)
echoKP ('template auto')


function UseTemplate ()
  executeKP ([[
    txt delete all
    txt left
    txt fill on
    txt font 3
    alias ~a "lua . TangleCommandDuplicate ({$0})"     % yuck!
    alias ~b "lua . TangleRandomPick ({$0})"           % yuck!
  ]])
  txtY = 15
  
  commandString = explode (" ", "1 2 2@ 3 3@ 4 4@ 23* 23*@ 0 i $ $@ $!z# $$* $$*@")
  for i = 1, #commandString do
    executeKP ("txt 15 " .. txtY .. ' " ' .. commandString [i] ..
        ' " "' .. '~a ' .. commandString [i] .. '"')
    txtY = txtY + 25
  end
  
  executeKP ([[
    txt fill off
    txt lineskip -25
    txt 10 a "embed in all:"
    txt fill on
  ]])
  
  txtY = txtY + 50
  
  commandString = explode (" ", "1,1@ 1,0 1,1,0 1,1,1,0 $,$@ 1,0,i,1z")
  for i = 1, #commandString do
    executeKP ("txt 15 " .. txtY .. ' " ' .. commandString [i] ..
        ' " "' .. '~b ' .. commandString [i] .. '"')
    txtY = txtY + 25
  end
  
  executeKP ([[
    txt fill off
    txt 10 a "choose randomly:"
  ]])

  numTHs = NumberTangleHoldersInTemplate ()
  --print ("number of tangle holders is " .. numTHs)

  TangleCommand ("1", true)
  Title ("Embedding tangles into the " .. knotName .. " template")
  AddHiddenButtons ()
end
 
function RandomChoiceText (commands, didDoIt)
  local choice = explode (",", commands)
  local text = "randomly "
  if didDoIt then
    text = text .. "embedded"
  else
    text = text .. "embedding"
  end
  
  text = text .. " one of "
  for i = 1, #choice do
    text = text .. choice [i] .. " "
  end
  text = text .. "into each slot"

  executeKP ('txt centre;txt c -40 "' .. text .. '"')
  --print ('txt centre;txt c -40 "' .. text .. '"')
end

function TangleRandomPick (commands)
  local c = ""
  for i = 1, numTHs do
    c = c .. chooseKP (commands)
  end
  TangleCommand (c, false)
  
  RandomChoiceText (commands, true)
end

function TangleCommandDuplicate (commands)
  TangleCommand (commands, true)
end
 
function Finish (stringOfOneCharacterCommands, tangleCommand)
  CheckSafe ()
  CreateMeta (tangleCommand)
  --print ("Finish:  " .. stringOfOneCharacterCommands .. " " .. tangleCommand)
  
  executeKP ([[
    sradius = 0.7
    go
    txt group 842377 on
    #6 echo
    echo equivalent to entering the following command:
    txt fill off
    txt centre
    name init
  ]])
  echoKP (tangleCommand)
  
  executeKP ('txt c -40 "' .. 'embedded tangle ' ..
             stringOfOneCharacterCommands .. ' into all slots of template"' )
  executeKP ('txt c -60 "click on one of the buttons on the left to embed another tangle"')

end
 
firstCall = true

function TangleCommand (stringOfOneCharacterCommands, duplicate)
  if firstCall then
    firstCall = false
    executeKP ("vscale = 0.12")
  end
    
  local tangleCommand = "tangle " .. stringOfOneCharacterCommands
  if duplicate then tangleCommand = tangleCommand .. "`" end
  tangleCommand = tangleCommand .. 't'
  
  executeKP (tangleCommand)
  BotTitle (tangleCommand)

  Finish (stringOfOneCharacterCommands, tangleCommand)
end

function CheckSafe ()
  if Safe () then executeKP ("txt delete group 42") return end
  
  executeKP ([[
    txt push
    txt fill off
    txt font 4
    txt centre
    txt group 42
    txt c 55 "not safe"
    txt pop
    tfunc 3 "lua . CheckSafe ()"
  ]])
end

function NumberTangleHoldersInTemplate ()
  local info = lcaptureKP ("tholder")
  return info [#info]
end

function CreateMeta (tc)
  executeKP ("meta -info")
  executeKP ('meta tcalc "' .. tc .. '"')
  executeKP ('meta template "' .. knotName .. '"')
  executeKP ('meta numTHs ' .. numTHs)
end

function TangleRandomPick2 (commands)
  randomClaspTangleCommand = "tangle "   -- note this is global
  for i = 1, numTHs do
    randomClaspTangleCommand = randomClaspTangleCommand .. chooseKP (commands)
  end
  randomClaspTangleCommand = randomClaspTangleCommand .. "t"
  executeKP (randomClaspTangleCommand)
  BotTitle (randomClaspTangleCommand)
end

desiredN = 0
timeLimitForClasping = 9
didAskToUnlimit = false

function AskToUnlimit ()
  if didAskToUnlimit then return end
  executeKP ([[
    txt push
    txt font 4
    txt centre
    txt fill on
    txt expire 9
    txt c 70 "remove time limit" "txt delete remove;lua . timeLimitForClasping = 999999"
    txt font 3
    txt fill off
    txt c 45 "ignore the button above to retain time limit"
    txt pop
  ]])
  didAskToUnlimit = true
end

function NComponents (N)
  executeKP ("txt group 842377 off")
  RandomChoiceText ("$,$@,$z,$@z", false)
  desiredN = N
  local message = "randomly embedding clasps to try to get " .. Plural (desiredN, "string")
  --echoKP (message)
  EphemeralMessage (message)
  
  DoUntil (EmbedClasps, Test, timeLimitForClasping, Result)
end

function EmbedClasps ()
  TangleRandomPick2 ("$,$@,$z,$@z")
end

function Test ()
  return paramKP ("ncomp") == desiredN
end

function Result (timetaken, numsteps, timedOut)
  if timedOut then
    message = "can't do it after " .. Plural (numsteps, "trial")
    echoKP (message)
    executeKP ([[
      go 0
      txt group 842377 off
     ]])
    EphemeralMessage (message)
    AskToUnlimit ()
  else
    EphemeralMessage (" ")
    Finish ("gumby", randomClaspTangleCommand)
    echoKP (string.format ("%.2f seconds, ", timetaken) ..
            Plural (numsteps, "trial") .. ", " .. Plural (paramKP ("ncomp"), "component"))
  end
  RandomChoiceText ("$,$@,$z,$@z", true)
end

function AddHiddenButtons ()   -- not hidden yet!
  executeKP ([[
  txt push
  txt group 842376
  txt right
  txt font 3
  txt fill on
  txt lineskip -22
  ]])
  
  local yloc = 20
  for n = 9, 1, -1 do
    executeKP ("txt -15 " .. yloc .. ' " ' .. n .. ' " "n ' .. n ..'"')
    yloc = "a"
  end
  
  executeKP ([[
    txt fill off
    txt -10 a1.1 "N strings:"
    txt -10 a "try to get"
    
    txt group 842377
    txt fill on
    alias ~stoprel "go 0;txt group 842377 off"
    txt -15 a "stop relaxing" ~stoprel
    txt pop
  ]])
  
end

ShowSourceButton ()
