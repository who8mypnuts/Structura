
--[[

rob scharein
Thursday, 25-Jan-24 19:49:51 UTC

to do in KnotPlot: merge matching colours into one entry, as in
255 255 255 White,CanadaWhite,USAWhite

--]]


require "Vector3"

ColourUtils = {}
ColourUtils.verbose = false
  
-- https://flagpedia.net/index

local ColourSet = {  -- flag colours using demonym, can also use country name
  ["italy"] = "ItalianRed,ItalianWhite,ItalianGreen",
  ["canada"] = "CanadianRed,CanadianWhite",
  ["usa"] = "AmericanRed,AmericanWhite,AmericanBlue",
  ["ukraine"] = "UkrainianBlue,UkrainianYellow",
  ["sweden"] = "SwedishBlue, SwedishYellow",
  ["uk"] = "BritishBlue,BritishRed,BritishWhite",
  ["iceland"] = "IcelandicBlue,IcelandicRed,IcelandicWhite",
  ["germany"] = "GermanBlack,GermanRed,GermanGold",
  ["france"] = "FrenchBlue,FrenchWhite,FrenchRed",
  ["lithuania"] = "LithuanianYellow,LithuanianGreen,LithuanianRed",
  ["sad"] = "cerulean,cyan",
  ["mondrian"] = "MondrianBlack,MondrianRed,MondrianGrey,MondrianBlue,MondrianYellow"  -- 25 April 2024
}

-- set by ISO country code  https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes
ColourSet ["lt"] = ColourSet ["lithuania"]
ColourSet ["de"] = ColourSet ["germany"]
ColourSet ["ca"] = ColourSet ["canada"]
ColourSet ["is"] = ColourSet ["iceland"]
ColourSet ["it"] = ColourSet ["italy"]

function ColourUtils.sets ()
  for key,value in pairs (ColourSet) do
    echoKP (key .. ": " .. value)
  end
  return
end

function ColourUtils.ColourFromSet (colours)
  --[[
  
  colours each component with a colour chosen randomly from a
  set of comma separated colours, example usages:
  ColourUtils.ColourFromSet ("red,orange,yellow,green,cyan,blue,magenta")
  ColourUtils.ColourFromSet ("cerulean,cyan,blue")
  
  you can also use one of the predefined colour set defined above, as in
  ColourUtils.ColourFromSet ("Sweden")
  ColourUtils.ColourFromSet ("Canada")
  like all colour specifications in KnotPlot, case is ignored.

  --]]
  if RollDie == nil then
    echoKP ("needs RollDie() from Demo()")
    return
  end
  
  -- check to see if it is in ColourSet
  colours = string.lower (colours)
  if ColourSet [colours] ~= nil then
    colours = ColourSet [colours]
  end
  

  local com = "noop"   -- `no operation' command in KnotPlot, does nothing
  if ColourUtils.verbose then com = "echo" end

  local set = explode (",", colours)
  for c = 0, paramKP ("ncomps") - 1 do
    executeKP (set [RollDie (#set)], c, com, [[
      ARG3 colour ARG2 ARG1
      colour ARG2 ARG1
    ]])
  end
end


function check ()
  for key, value in pairs (ColourSet) do
    print ("[" .. key .. "] = " .. value)
  end
end


