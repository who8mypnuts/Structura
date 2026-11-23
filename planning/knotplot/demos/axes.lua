Demo ()
require "Primitives"

function FancyAxes ()
  Arrow (v3.zero, v3.xhat, 1, 102, "red")
  Arrow (v3.zero, v3.yhat, 1, 102, "green")
  Arrow (v3.zero, v3.zhat, 1, 102, "blue")

  Arrow (v3.zero, v3.mxhat, 1, 102, "cyan")
  Arrow (v3.zero, v3.myhat, 1, 102, "magenta")
  Arrow (v3.zero, v3.mzhat, 1, 102, "yellow")
end

executeKP ([[
  reset all
  scenery on
  show grid
  vscale = \rr[.7/1.4]
  rotate x \rr[-33/-77]
  rotate z \rr360
  txt on

  lua . Title ('Fancy Coordinate Axes')
  lua . FancyAxes ()
]])


BotButton ("rerun demo", "lua rerun")
ShowSourceButton ()

