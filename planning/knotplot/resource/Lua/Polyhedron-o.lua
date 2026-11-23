--[[

rob scharein, 15 April 2023
in the Public Domain

--]]

require "Vector3"

--  grep GLK Hart.txt | awk '{print $3, $4, $5}' | tr -d "(),;"  | awk '{printf ("%s,", $0);}'

hartColour = explode (",", "0.3 0.3 0.3,0.3 0.3 0.3,1 0.1 0.1,0.3 0.3 1,0.2 1.0 0.2,0.9 0.9 0.2,0 0 1,0.3 0 0.6,0.3 0.6 0.8,0.9 0.5 0.2,0.5 0.5 0.2,0.2 0.5 0.9,1 0.5 0.9,0.2 0.4 0.0,0.2 0.4 0.2,0.2 0.4 0.4,0.5 0.2 0.1,0.3 0.3 0.3");

Polyhedron = {}

Polyhedron.faceColouring = hartColour

function Polyhedron.new (name, vertex, face, centroid, normal, cofm)
  return {name = name, vertex = vertex, face = face, centroid = centroid, normal = normal, cofm = cofm}
end

function Polyhedron.compute (vertex, face)
  local centroid = {}
  local normal = {}
  for f = 1, #face do
    local vertices = {}
    for v = 1, #face [f] do
      table.insert (vertices, vertex [face [f][v]])
    end
    table.insert (centroid, Vector3.centroid (vertices))
    table.insert (normal, Vector3.normal (vertices))
  end
  local cofm = Vector3.centroid (vertex)
  return centroid, normal, cofm
end

function Polyhedron.scale (poly, scaleFactor)
  for i = 1, #poly.vertex do
    poly.vertex [i] = Vector3.mult (poly.vertex [i], scaleFactor)
  end
  local centroid, normal, cofm = Polyhedron.compute (poly.vertex, poly.face)
  return Polyhedron.new (poly.name, poly.vertex, poly.face, centroid, normal, cofm)
end

function Polyhedron.translate (poly, offset)
  for i = 1, #poly.vertex do
    poly.vertex [i] = Vector3.add (poly.vertex [i], offset)
  end
  local centroid, normal, cofm = Polyhedron.compute (poly.vertex, poly.face)
  return Polyhedron.new (poly.name, poly.vertex, poly.face, centroid, normal, cofm)
end

function Polyhedron.alignToTriangle (poly, triangle)
  Vector3.alignToTriangle (poly.vertex, triangle)
  local centroid, normal, cofm = Polyhedron.compute (poly.vertex, poly.face)
  return Polyhedron.new (poly.name, poly.vertex, poly.face, centroid, normal, cofm)
end

local mergeKount = 0

function Polyhedron.merge (polyTable)
  local nvert = 0
  local vertex = {}
  local face = {}
  
  local function adjust (faceTable)
    if nvert == 0 then return faceTable end
    faceTableAdjusted = {}
    for i = 1, #faceTable do
      table.insert (faceTableAdjusted, faceTable [i] + nvert)
    end
    return faceTableAdjusted
  end
  
  for i = 1, #polyTable do
    for v = 1, #polyTable [i].vertex do
      table.insert (vertex, polyTable [i].vertex [v])
    end
    for f = 1, #polyTable [i].face do
      table.insert (face, adjust (polyTable [i].face [f]))
    end
    nvert = nvert + #polyTable [i].vertex
  end
    
  local centroid, normal, cofm = Polyhedron.compute (vertex, face)
  mergeKount = mergeKount + 1
  return Polyhedron.new ("merge" .. mergeKount, vertex, face, centroid, normal, cofm)
end

function Polyhedron.rotateAboutZ (poly, angle)
  local a = Vector3.new (math.cos (angle), math.sin (angle), 0)
  angle = angle + 2 * math.pi / 3
  local b = Vector3.new (math.cos (angle), math.sin (angle), 0)
  angle = angle + 2 * math.pi / 3
  local c = Vector3.new (math.cos (angle), math.sin (angle), 0)
  return Polyhedron.alignToTriangle (poly, {a, b, c})
end

local fromOBJKount = 1

function Polyhedron.fromOBJ (objString)
  local name, numvert
  local face = {}
  local vertex = {}
  
  local line = explode ("\n", objString)
  for i = 1, #line do
    if string.len (line [i]) < 4 then goto continue end
    local v = explode (" ", line [i])
    if v [1] == "v" then
      table.insert (vertex, Vector3.new (v [2], v [3], v [4]))
    elseif v [1] == "f" then
      local F = {}
      for k = 2, #v do
        table.insert (F, tonumber (v [k]))
      end
      table.insert (face, F)
    else
      print ("ignoring " .. line [i])
    end
    ::continue::
  end
  
  name = "o" .. fromOBJKount
  fromOBJKount = fromOBJKount + 1
  
  local centroid, normal, cofm = Polyhedron.compute (vertex, face)
  return Polyhedron.new (name, vertex, face, centroid, normal, cofm)
end


function Polyhedron.fromEOBJ (eobjString)
  local name, numvert
  local face = {}
  local vertex = {}
  
  local line = explode ("\n", eobjString)
  for i = 1, #line do
    if i == 1 then
      name = string.sub (line [1], 3, -1)
    elseif i == 2 then
      numvert = tonumber (line [i])
    elseif #vertex < numvert then
      local v = explode (" ", line [i])
      table.insert (vertex, Vector3.new (v [1], v [2], v [3]))
    elseif string.sub (line [i], 1, 2) == "f " then
      local f = explode (" ", line [i])
      local F = {}
      for k = 2, #f do
        table.insert (F, tonumber (f [k]) + 1)
      end
      table.insert (face, F)
    end
  end
  
  local centroid, normal, cofm = Polyhedron.compute (vertex, face)
  return Polyhedron.new (name, vertex, face, centroid, normal, cofm)
end

function Polyhedron.print (poly)
  print (poly.name)
  for i = 1, #poly.vertex do
    print (Vector3.String (poly.vertex [i]))
  end
  for i = 1, #poly.face do
    local f = ""
    for k = 1, #poly.face [i] do
      if poly.face [i][k] < 1 or poly.face [i][k] > #poly.vertex then
        print ("bad index of " .. poly.face [i][k])
        return
      end
      f = f .. poly.face [i][k] .. " "
    end
    print (f)
  end
end

function Polyhedron.bounds (poly)
  local min = Vector3.positiveInfinity
  local max = Vector3.negativeInfinity
  
  --print ("\n\nin bounds:")
  --print (Vector3.String (min))
  --print (Vector3.String (max))

  for i = 1, #poly.vertex do
    --print ("i is: " .. i)
    --print ("min is " .. Vector3.String (min))
    --print ("veretex is " .. Vector3.String (poly.vertex [i]))
    min = Vector3.min (min, poly.vertex [i])
    max = Vector3.max (max, poly.vertex [i])
  end
  return min, max
end
  
function Polyhedron.toEOBJ (poly)
  segs = {}
  local function SetSeg (a, b)
    local s
    if a < b then
      s = "s " .. a .. " " .. b
    else
      s = "s " .. b .. " " .. a
    end
    table.insert (segs, s)
  end
  local prev = 0
  local eobj = "# " .. poly.name .. "\n" .. #poly.vertex .. "\n"
  for i = 1, #poly.vertex do
    eobj = eobj .. Vector3.String (poly.vertex [i]) .. "\n"
  end
  for i = 1, #poly.face do
    if prev ~= #poly.face [i] then
      eobj = eobj .. "c " .. Polyhedron.faceColouring [math.min (#poly.face [i], #Polyhedron.faceColouring)] .. "\n"
      prev = #poly.face [i]
    end
    
    local f = "f"
    for k = 1, #poly.face [i] do
      f = f .. " " .. (poly.face [i][k] - 1)
      kn = k % #poly.face [i] + 1
      SetSeg (poly.face [i][k] - 1,
              poly.face [i][kn] - 1)
    end

    eobj = eobj .. f .. "\n"
  end
  
  eobj = eobj .. "L 2\nc 0 0 0\n"
  
  table.sort (segs)
  prev = ""
  for k,v in ipairs (segs) do
    if v ~= prev then
      eobj = eobj .. v .. "\n"
      prev = v
    end
  end
  
  return eobj
end

local fromKPKount = 1

function Polyhedron.fromKP ()
  local vertex = {}
  local face = {}
  local ncomp = paramKP ("ncomp")
  if ncomp == 0 then echoKP ("nothing loaded") return end
  
  local name = captureKP ("name")
  if name == "knot is not named" then
    name = "p" .. fromKPKount
    fromKPKount = fromKPKount + 1
  end
  local nbeads = paramKP ("nbeads")
  
  local total = 0
  for c = 1, ncomp do
    local beads = getComponentKP (c - 1)
    local f = {}
    for b = 1, #beads do
      table.insert (vertex, beads [b])
      table.insert (f, total + b)
    end
    table.insert (face, f)
    total = total + #beads
  end
  
  local centroid, normal, cofm = Polyhedron.compute (vertex, face)
  return Polyhedron.new (name, vertex, face, centroid, normal, cofm)
end

  

