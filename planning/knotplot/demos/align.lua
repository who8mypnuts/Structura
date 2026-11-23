executeKP ([[

reset all
sradius = 0.1
knot \ri[2/3]
centre mass
%show grid
txt on
txt font 4
txt centre
project random
txt fill on
txt -40 c "align" "align axes keep;lua . Arros()"

rotate x \rr360
rotate y \rr360
rotate z \rr360

scenery on
]])

Demo ()
require "Primitives"


function Label (base, dir, scale, label)
  local pos = Vector3.add (base, Vector3.mult (dir, scale * 1.2))
  executeKP (Vector3.String (pos), label, [[
    txt push
    txt fill off
    txt font 4
    txt ARG1 "ARG2"
    txt pop
  ]])
end

function Arros ()
  executeKP ("scenery delete;txt delete group 33;txt group 33")
  executeKP ("txt delete group 33")
  echoKP ("--> txt delete group 33")

  info = lcaptureKP ("cofm uvwc")

  uhat = Vector3.new (info [1], info [2], info [3])
  vhat = Vector3.new (info [4], info [5], info [6])
  what = Vector3.new (info [7], info [8], info [9])
  cofm = Vector3.new (info [10], info [11], info [12])

  Arrow (v3.zero, v3.xhat, 3, 22, "red")
  Arrow (v3.zero, v3.yhat, 3, 22, "green")
  Arrow (v3.zero, v3.zhat, 3, 22, "blue")

  Arrow (cofm, uhat, 2, 22, "cyan")
  Arrow (cofm, vhat, 2, 22, "magenta")
  Arrow (cofm, what, 2, 22, "yellow")
  
  Label (v3.zero, v3.xhat, 3, "X")
  Label (v3.zero, v3.yhat, 3, "Y")
  Label (v3.zero, v3.zhat, 3, "Z")
  Label (cofm, uhat, 2, "u")
  Label (cofm, vhat, 2, "v")
  Label (cofm, what, 2, "w")
  
  executeKP ("display true")
end

Arros ()
  
