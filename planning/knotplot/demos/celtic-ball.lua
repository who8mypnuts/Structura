Demo ()

if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    load celtic2.k
    %load eepT.k
    %load aaaaH.k
    verbose = false
    tfunc reset
    vscale = 0.39
    par vscale
    sradius = 0.12
    txt on
    txt clobber on
    txt font 3
    txt centre
  ]])
  ShowSourceButton ()
end

if FlipCoin () then
  breakline = "secondary"
else
  breakline = "primary"
end

numberStrings = Random ("ri[1/11]")

Title ("trying to get " .. Plural (numberStrings, "string") ..
       " by setting " .. breakline .. " breaklines")
       
function CreateCeltic ()
  prob = Random ("rr.4")
  celticCommand = "celtic random " .. breakline .. " " .. prob
  BotTitle (celticCommand)
  executeKP (celticCommand .. ";celtic copy")
end

function Test ()
  return numberStrings == paramKP ("ncomp")
end

function Result (timeTaken, numberSteps, timedOut)
  if not timedOut then
    Title ("Done!")
    local message = "took " .. string.format ("%.1f", timeTaken) .. " seconds, " ..
              Plural (numberSteps, "try") .. ", " .. Plural (paramKP ("ncomps"), "string")
    BotTitle (message)
    echoKP ("\n\n\n" .. message)
  end
end

DoUntil (CreateCeltic, Test, 123456, Result)





