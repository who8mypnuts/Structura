--[[

 rob scharein, 7 feb 2023

--]]

-- https://en.wikipedia.org/wiki/List_of_Crayola_crayon_colors
-- https://crayola.fandom.com/wiki/List_of_core_crayon_colors

Demo ()

require "Primitives"

function SetBackgroundColour (R, G, B, colourName)
  executeKP ("background = rgbi:" .. R .. "/" .. G .. "/" .. B)
  print (colourName)
  executeKP ("txt colour rgbi:" .. 255 - R .. "/" .. 255 - G .. "/" .. 255 - B)
  --print ("txt colour rgbi:" .. 255 - R .. "/" .. 255 - G .. "/" .. 255 - B)
  executeKP ([[
    txt c -40 "hover your mouse over one of the blocks"
    txt c -60 "click on a block to set the background colour to that block's colour"
  ]])
  executeKP ("display true")
  Title ("Colour")
  BotTitle (colourName)
end

if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    silent = true
    colour show
    silent = false
    vscale = 0.281023
    txt on
    txt clobber on
    txt centre
    txt font 3
    alias ~clickOnColour "lua . SetBackgroundColour ($0, $1, $2, '$3')"
    ~clickOnColour 0 0 0 black
    txt delete black
    scenery on
  ]])
  
  colourOrigin = Vector3.new (-10, -10, -10)
  Arrow (colourOrigin, v3.xhat, 1, 102, "red")
  Arrow (colourOrigin, v3.yhat, 1, 102, "green")
  Arrow (colourOrigin, v3.zhat, 1, 102, "blue")

end

executeKP ([[
  % this doesn't generate a uniform random rotation
  rotate i \rr360
  rotate j \rr360
  rotate k \rr360
]])

--[[

 don't use knot components as hover-over objects
 
 these should be blocks or scenery

--]]

