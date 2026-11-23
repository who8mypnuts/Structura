--[[

rob scharein
Friday, 01-Mar-24 05:27:52 UTC

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    mode cb
    alias -e msn "lua . Start ($0, false)"
  ]])

  Demo ()
  Title ("Minimal Step Number - Torus Knots / Links")
  

end   -- end of init block

ButtonHelp ()
ButtonStack ("toggle:,grid,show ~grid,fullscreen,full toggle")
ButtonStack ("action:"
          .. ",start,lua . Start (RollDie (33))"
          .. ",embed,lua . Embed ()"
          .. ",record,lua . Record ()"
          .. ",retrieve,lua . Retrieve ()"
          .. ",save,lua . Save ()"
          .. ",check,lua . Check ()"
          )
          
function DisableAll ()
  canEmbed = false
  canRecord = false
  canRetrieve = false
  canSave = false
end
  
saveName = "unknown"


torusM = 0
torusN = 0

function Start (n, blurt)
  if blurt == nil then blurt = true end
  
  local function Blurt ()
    executeKP (n, [[
      echo **************
      echo you can use the msn alias to get
      echo specific torus knot / link, your
      echo click was equivalent to entering
      echo "  " msn ARG1
      echo into this window
    ]])
  end
  
  executeKP (n, [[
    untran
    sradius = 0.45
    vscale = 0.35
    tfunction reset
    clk init
    torus number ARG1 1022
    mode s
  ]])
  
  if blurt then Blurt () end
  
  DisableAll ()
  canEmbed = true
    
  local name = lcaptureKP ("name")
  local info = lcaptureKP ('info s')
  SubTitle ("T " .. name [#name - 1] .. " " .. name [#name] .. ", " ..
            Plural (tonumber (info [1]), "component"))
  torusM = string.sub (name [#name - 1], 2, -2)
  torusN = string.sub (name [#name], 1, -2)
  saveName = "T" .. torusM .. "-" .. torusN
  print (saveName, torusM, torusN)
end

function Embed ()
  if not canEmbed then
    EphemeralMessage ("click on start button")
    return
  end
  
  DisableAll ()
  canRecord = true
  
  EphemeralMessage ("knot is too large to see right now")
  
  executeKP ([[
    fitto 111
    embed clk
    clk init
    clk load
    clk centre on
    
    tfunction reset
    tfunction 1 "clk z \rr.21" 0 rep 1 11
    tfunction 1 "clk z \rr[.09/.15]" 0 rep 1 11
    tfunction 1 "clk z .21" 0 rep 7 22

    tfunction 2 "lua . EphemeralMessage ('wait a few seconds, then click record button')"
    
    energy model nbead
    energy format "Nedges = %.0f"
    show energy
    clk run 1000000


  ]])
  canRecord = true
  
end

function Record ()
  if not canRecord then
    EphemeralMessage ("click on embed button")
    return
  end
  
  local info = lcaptureKP ("info s")
  if tonumber (info [2]) > 250 then
    EphemeralMessage ("can't record because knot too big")
    return
  end
  
  DisableAll ()
  canRetrieve = true
 
  executeKP ([[
    clk target 9999
    clk search on
  ]])
  
end

function Retrieve ()
  if not canRetrieve then
    EphemeralMessage ("click on record button")
    return
  end
  
  executeKP ([[
    clk stop
    tfunction reset
    load |min
    centre
    jitter 0
  ]])
  
  DisableAll ()
  canSave = true
end

function Save ()
  if not canSave then
    EphemeralMessage ("click on the retrieve button")
    return
  end
  local info = lcaptureKP ("info s")
  lastSaved = saveName .. "-" .. info [2] .. ".txt"
  executeKP (lastSaved, [[
    echo save ARG1  newsud
    save ARG1  newsud
  ]])
  
  DisableAll ()
  canCheck = true
  
end

function Check ()
  if not canCheck then
    EphemeralMessage ("first save something")
    return
  end
  
  local poly = chooseKP ("homfly flypmoth homfly-pt homflypt")
  
  EphemeralMessage ("loading last save and relaxing")
  executeKP (lastSaved, [[
    load ARG1
    ago 99
    align axes
    untran
    jitter .1   % add a small amount of noise to avoid non-general position
    display true
  ]])
  
  EphemeralMessage ("checking " .. poly .. " polynomial")
  local result = captureKP (poly)
  executeKP (poly, result, [[
    echo ARG1 polynomial is
    echo ARG2
    echo -f
    display true
    nap 1
  ]])
  EphemeralMessage ("seeing what " .. poly .. " should be")
  
  
  executeKP (torusM, torusN, [[
    torus ARG1 ARG2  333
    echo -f
    ago 44
    display true
    nap 1
  ]])
  
  local whatisit = captureKP (poly)
  executeKP (whatisit, poly, [[
    echo whearas ARG2 polynomial should be
    echo ARG1
  ]])
  
  if result == whatisit then
    EphemeralMessage (poly .. " polynomials match!")
  else
    EphemeralMessage (poly .. " polynomials differ!")
  end

  
end

Start (RollDie (22))

--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
