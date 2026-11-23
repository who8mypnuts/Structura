-- 24 March 2022, Rob Scharein
-- in the Public Domain


Vector3 = {}

function Vector3.new (x, y, z)
  if z == nil then z = 0
  return {x = x, y = y, z = z}
end

function Vector3.copy (a)
  return Vector3.new (a.x, a.y, a.z)
end

Vector3.zero = Vector3.new (0, 0, 0)
Vector3.origin = Vector3.new (0, 0, 0)
Vector3.xhat = Vector3.new (1, 0, 0)
Vector3.yhat = Vector3.new (0, 1, 0)
Vector3.zhat = Vector3.new (0, 0, 1)
Vector3.mxhat = Vector3.new (-1, 0, 0)
Vector3.myhat = Vector3.new (0, -1, 0)
Vector3.mzhat = Vector3.new (0, 0, -1)
Vector3.positiveInfinity = Vector3.new (1.022e9, 1.022e9, 1.022e9)
Vector3.negativeInfinity = Vector3.new (-1.022e9, -1.022e9, -1.022e9)


function Vector3.min (a, b)
  --print ("a is " .. Vector3.String (a))
  --print ("b is " .. Vector3.String (b))
  return Vector3.new (
    math.min (tonumber (a.x), tonumber (b.x)),
    math.min (tonumber (a.y), tonumber (b.y)),
    math.min (tonumber (a.z), tonumber (b.z))
    )
end

function Vector3.max (a, b)
  --print ("a is " .. Vector3.String (a))
  --print ("b is " .. Vector3.String (b))
  return Vector3.new (
    math.max (tonumber (a.x), tonumber (b.x)),
    math.max (tonumber (a.y), tonumber (b.y)),
    math.max (tonumber (a.z), tonumber (b.z))
    )
end

function Vector3.add (a, b)
  return Vector3.new (a.x + b.x,
                      a.y + b.y,
                      a.z + b.z)
end

function Vector3.sub (a, b)
  return Vector3.new (a.x - b.x,
                      a.y - b.y,
                      a.z - b.z)
end

function Vector3.length (v)
  return math.sqrt (v.x * v.x + v.y * v.y + v.z * v.z)
end

function Vector3.distance (v1, v2)
  local v = Vector3.sub (v1, v2)
  return Vector3.length (v)
end

function Vector3.tostring (v)
  return "(" .. v.x .. ", " .. v.y .. ", " .. v.z .. ")"
end

function Vector3.value (v)
  return v.x .. " " .. v.y .. " " .. v.z
end

function Vector3.dot (v, w)
  return v.x * w.x + v.y * w.y + v.z * w.z
end

function Vector3.cross (w, z)
  return Vector3.new (w.y * z.z - w.z * z.y,
                      w.z * z.x - w.x * z.z,
                      w.x * z.y - w.y * z.x)
end

function Vector3.mult (v1, factor)
  return Vector3.new (factor * v1.x,
                      factor * v1.y,
                      factor * v1.z)
end

function Vector3.normalized (v)
  local length = Vector3.length (v)
  -- warning: doesn't check for zero length
  return Vector3.new (v.x / length, v.y / length, v.z / length)
end

function Vector3.interpolate (a, b, p)
  return Vector3.add (Vector3.mult (a, 1 - p), Vector3.mult (b, p))
end

function Vector3.midpoint (a, b)
  return Vector3.mult (Vector3.add (a, b), 0.5)
end

function Vector3.perp (b)
  -- warning: not continuous
  -- see https://en.wikipedia.org/wiki/Hairy_ball_theorem
  if b.z * b.z > b.x * b.x + b.y * b.y then
    return Vector3.cross (b, Vector3.xhat)
  else
    return Vector3.cross (b, Vector3.zhat)
  end
end

function Vector3.angle (a, b)
  return math.acos (Vector3.dot (Vector3.normalized (a),
                                 Vector3.normalized (b)))
end

function Vector3.Triad (g)
  -- given a vector g, return an orthonormal triad {u, v, w} with w in the direction of g
  local w = Vector3.normalized (g)
  local u = Vector3.normalized (Vector3.perp (w))
  local v = Vector3.cross (w, u)
  --print ("u " .. Vector3.String (u))
  --print ("v " .. Vector3.String (v))
  --print ("w " .. Vector3.String (w))
  return {u, v, w}
end

function Vector3.String (v)
  return v.x .. " " .. v.y .. " " .. v.z
end

function Vector3.printArc (arc)  -- a table of Vector3
  for i = 1, #arc do
    print (Vector3.String (arc [i]))
  end
end

Vector3.String_zUp = Vector3.String

function Vector3.String_yUp (v)
  return v.z .. " " .. v.x .. " " .. v.y
end

function Vector3.String_xUp (v)
  return v.y .. " " .. v.z .. " " .. v.x
end

function Vector3.centroid (vtable)   -- table of Vector3s
  local sum = Vector3.zero
  for i = 1, #vtable do
    sum = Vector3.add (sum, vtable [i])
  end
  return Vector3.mult (sum, 1 / #vtable)
end

function Vector3.normal (vtable)   -- table of Vector3s
  local v21 = Vector3.sub (vtable [2], vtable [1])
  local v31 = Vector3.sub (vtable [3], vtable [1])
  return Vector3.normalized (Vector3.cross (v21, v31))
end

function Vector3.alignToTriangle (points,    -- table of Points
                                  triangle)  -- a triangle
  local centroid = Vector3.centroid (triangle)
  for i = 1, #points do
    points [i] = Vector3.sub (points [i], centroid)
  end
  
  local a = Vector3.sub (triangle [2], triangle [1])
  local b = Vector3.sub (triangle [3], triangle [1])
  local w = Vector3.normalized (Vector3.cross (a, b))
  local u = Vector3.normalized (Vector3.sub (triangle [1], centroid))
  local v = Vector3.cross (w, u)
  Vector3.alignTriadToWorld (points, {u, v, w})
end

function Vector3.alignTriadToWorld (points, -- table of Points
                                    triad)
  for i = 1, #points do
    local x, y, z
    x = Vector3.dot (points [i], triad [1])
    y = Vector3.dot (points [i], triad [2])
    z = Vector3.dot (points [i], triad [3])
    points [i] = Vector3.new (x, y, z)
  end
end

function Vector3.rectangularToSpherical (x, y, z)
  local r = math.sqrt (x * x + y * y + z * z)
  if r == 0 then
    return 0, 0, 0
  end
  local theta = math.acos (z / r)
  local phi = math.atan2 (y, x)
  return r, theta, phi
end
 

function Vector3.unitVector (theta, -- pi / 2 - latitude
                             phi)   -- longitude
  -- creates a unit vector v from spherical coordinates theta, phi
  return Vector3.new (math.sin (theta) * math.cos (phi),
                      math.sin (theta) * math.sin (phi),
                      math.cos (theta));
end

  
function Vector3.rectFrame (distance, altitude, azimuth, width, height)
  --print (" 0: " .. Vector3.String (Vector3.unitVector (0, 0)))
  --print (" pi / 2: " .. Vector3.String (Vector3.unitVector (math.pi / 10, 0)))
  --print (" -pi / 2: " .. Vector3.String (Vector3.unitVector (-math.pi / 10, 0)))
  -- creates a rectagular frame facing a viewer at the origin
  local uv = Vector3.unitVector (math.rad (90 - altitude), math.rad (azimuth))
  --print (Vector3.String (uv))
  local triad = Vector3.Triad (uv)
  --print (Vector3.String (triad [2]))
  local location = Vector3.mult (triad [3], distance)
  local uspan = Vector3.mult (triad [1], width / 2.0)
  local vspan = Vector3.mult (triad [2], height / 2.0)
  return {Vector3.sub (Vector3.add (location, uspan), vspan), -- lower left
          Vector3.sub (Vector3.sub (location, uspan), vspan), -- lower right
          Vector3.add (Vector3.sub (location, uspan), vspan), -- upper right
          Vector3.add (Vector3.add (location, uspan), vspan)} -- upper left
end


Point = Vector3

-- return Vector3


-- see https://github.com/themousery/vector.lua
-- to figure out how to make this object oriented


