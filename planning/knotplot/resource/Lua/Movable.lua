--[[

rob scharein
Monday, 2024 August 5, 13:10:23 PDT

--]]

require "Vector3"

Movable = {}
Movable.group = 1555000772

function Movable.New (create, x, y, colour, radius)

  local movable = setmetatable ({}, Movable)
  movable.x = x
  movable.y = y
  
  movable.colour = colour
  movable.radius = radius
  movable.group = Movable.group
  
  movable.p = {}
  movable.q = {}
  movable.space = 5  -- Bezier control point spacing
  
  local function remake ()
    movable.location = Vector3.new (movable.x, movable.y, 0)
    movable.p = {}
    movable.q = {}
    movable.inp = {}
    movable.outp = {}
    for i = 1, 4 do
      local p = Vector3.add (movable.location,
                             Vector3.mult (Vector3.incr [i], movable.radius))
      table.insert (movable.p, p)
      local q = Vector3.add (p, Vector3.mult (Vector3.incr [i], movable.space))
      table.insert (movable.q, q)
      table.insert (movable.inp, {q, p})
      table.insert (movable.outp, {p, q})
    end
                             
    create (movable.x, movable.y, movable.colour, movable.radius, movable.group)
  end
  
  remake ()

  movable.moveTo =
    function (x, y)
      movable.x = x
      movable.y = y
      remake ()
    end
  
  movable.hoveringOver =
    function (x, y)
      local v = Vector3.new (x, y, 0)
      if Vector3.distance (v, movable.location) <= movable.radius then
        return true
      else
        return false
      end
    end

  Movable.group = Movable.group + 1
  return movable
end

return Movable

