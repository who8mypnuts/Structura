require "Vector3"

function Quad (a, b, c, d, colourName, alpha, twoSided)
  local colour = Colour (colourName)
  
  data = "# quad\n4\n" ..
        a.x .. " " .. a.y .. " " .. a.z .. "\n" ..
        b.x .. " " .. b.y .. " " .. b.z .. "\n" ..
        c.x .. " " .. c.y .. " " .. c.z .. "\n" ..
        d.x .. " " .. d.y .. " " .. d.z .. "\n" ..
        "c " .. colour .. "\n" ..
        "a " .. tonumber (alpha)  .. "\n" ..
        "f 0 1 2 3"
  if twoSided then
    data = data .. "\nf 3 2 1 0"
  end
  sceneryKP (data)
end

v3 = Vector3

function Polygon (points, first, last, colourName)
  local colour = Colour (colourName)
  local size = math.max (first, last)
  local data = "# " .. size .. "-sided polygon\n" .. size .. "\n"
  local incr = 1
  if last < first then incr = -1 end

  local v
  for v = 1, size do
    local p = points [v]
    data = data ..  p.x .. " " .. p.y .. " " .. p.z .. "\n"
  end
  data = data .. "c " .. colour .. "\n"
  local face = "f"
  for i = first, last, incr do
    face = face .. " " .. (i - 1)
  end
  data = data .. face .. "\n"
  -- print (data)
  sceneryKP (data)
end


function Cone (top, bottom, topRadius, bottomRadius, nsegs, colourName)
  local diff = v3.sub (top, bottom)
  local u = v3.perp (diff)
  local v = v3.cross (diff, u)
  ut = v3.mult (v3.normalized (u), topRadius)
  vt = v3.mult (v3.normalized (v), topRadius)
  ub = v3.mult (v3.normalized (u), bottomRadius)
  vb = v3.mult (v3.normalized (v), bottomRadius)

  local theta = 0.0
  local thetaIncr = 2.0 * math.pi / nsegs
  local i = 0
  topCap = {}
  botCap = {}
  
  repeat
    et = v3.add (v3.mult (ut, math.cos (theta)),
                v3.mult (vt, math.sin (theta)))
    ft = v3.add (v3.mult (ut, math.cos (theta + thetaIncr)),
                v3.mult (vt, math.sin (theta + thetaIncr)))
    eb = v3.add (v3.mult (ub, math.cos (theta)),
                v3.mult (vb, math.sin (theta)))
    fb = v3.add (v3.mult (ub, math.cos (theta + thetaIncr)),
                v3.mult (vb, math.sin (theta + thetaIncr)))
    b = v3.add (top, et)
    a = v3.add (top, ft)
    d = v3.add (bottom, fb)
    c = v3.add (bottom, eb)
    
    Quad (a, b, c, d, colourName, 1, false)
    table.insert (topCap, b)
    table.insert (botCap, c)
    
    theta = theta + thetaIncr
    i = i + 1
  until (i == nsegs)
  Polygon (topCap, 1, nsegs, colourName)
  Polygon (botCap, nsegs, 1, colourName)
end

function Cylinder (top, bottom, radius, nsegs, colourName)
  --if nsegs == nil then nsegs = 12 end
  --if colourName == nil then colourName = "KnotPlot Orange" end
  Cone (top, bottom, radius, radius, nsegs, colourName)
end

function CylinderPath (point, radius, nsegs, colourName, closed)  -- closed is an optional argument
  for i = 1, #point - 1 do                                        -- if ommited, then path is open  
    Cylinder (point [i], point [i + 1], radius, nsegs, colourName)
  end
  if closed == true then
    Cylinder (point [#point], point [1], radius, nsegs, colourName)
  end
end

function Plane (centre, normal, width, height, colourName, alpha, twoSided)
  local triad = v3.Triad (normal)
  local u = v3.mult (triad [1], width)
  local v = v3.mult (triad [2], height)
  ll = v3.sub (v3.sub (centre, u), v)
  lr = v3.sub (v3.add (centre, u), v)
  ur = v3.add (v3.add (centre, u), v)
  ul = v3.add (v3.sub (centre, u), v)
  Quad (ll, lr, ur, ul, colourName, alpha, twoSided)
end

function Disc (centre, normal, size, aspect, angle, nsegs, colourName, alpha, twoSided)
  local triad = v3.Triad (normal)

end

function SimpleDisc (xcen, ycen, zcen,
                     width, height,
                     nsegs,
                     colourName,
                     alpha)         -- 0 to 1
  local data = "# " .. nsegs .. "-sided disc\n" .. nsegs .. "\n"
  local theta = 0
  local thetaIncr = 2 * math.pi / nsegs
  local face = "f"
  --print (colourName)
  for i = 0, nsegs - 1 do
    local x = xcen + math.cos (theta) * width / 2
    local y = ycen + math.sin (theta) * height / 2
    local z = zcen
    data = data .. x .. " " .. y .. " " .. z .. "\n"
    face = face .. " " .. i
    theta = theta + thetaIncr
  end
  data = data .. "c " .. Colour (colourName) .. "\n" ..
                 "a " .. tonumber (alpha) .. "\n" .. face .. "\n"
  
  --print ("\n\n>>>>\n" .. data .. "<<<<\n")
  sceneryKP (data)
end

function Annulus (location,             -- Vector3
                  width, aspect, angle, -- aspect and angle not yet used
                  thickness, nsegs,
                  colourName,
                  alpha,
                  returnData)
  
  local data = "# " .. nsegs .. "-sided annulus of thickness " .. thickness .. "\n" .. 2 * nsegs .. "\n"
  local outer = ""
  local inner = ""
  local theta = (angle * math.pi / 180)
  local thetaIncr = 2 * math.pi / nsegs
  local face = ""
  
  
  
  for i = 0, nsegs - 1 do
    j = (i + 1) % nsegs
    local xin = aspect * location.x + math.cos (theta) * width / 2
    local yin = location.y + math.sin (theta) * width / 2
    local z = location.z
    local xout = location.x + math.cos (theta) * (width + thickness) / 2
    local yout = location.y + math.sin (theta) * (width + thickness) / 2
    outer = outer .. xout .. " " .. yout .. " " .. z .. "\n"
    inner = inner .. xin  .. " " .. yin  .. " " .. z .. "\n"
    face = face .. "f " .. i .. " " .. j .. " " .. j + nsegs .. " " .. i + nsegs .. "\n"
    theta = theta + thetaIncr
  end
 
  data = data .. outer .. inner
  
  data = data .. "c " .. Colour (colourName) .. "\n" ..
                 "a " .. tonumber (alpha) .. "\n" .. face
  if returnData then
    return data
  else
    sceneryKP (data)
  end
end

function Arrow (loc, dir, length, nsegs, colourName)
  local location = v3.copy (loc)
  local direction = v3.copy (dir)
  tail = location
  midp = v3.add (location, v3.mult (v3.normalized (direction), 5 * length / 6.5))
  tip = v3.add (location, v3.mult (v3.normalized (direction), length))
  Cone (midp, tip, 0.12 * length, 0,  nsegs, colourName)
  Cylinder (tail, midp, 0.06 * length, nsegs, colourName)
end

function xyzAxes (nsegs)
  if nsegs == nil then nsegs = 12 end
  Arrow (v3.zero, v3.xhat, 2, nsegs, "red")
  Arrow (v3.zero, v3.yhat, 2, nsegs, "green")
  Arrow (v3.zero, v3.zhat, 2, nsegs, "blue")
end

function BoundingBox (colourName, padding)
  if colourName == nil then colourName = 'green' end
  
  -- padding could be set to the current value of sradius or cradius
  -- if you want to see the bounding box of the thickened knot
  if padding == nil then padding = 0.0 end
  
  local s = "# bounding box\n8\n"
  local l = lcaptureKP ("info s")
  
  local min = Vector3.new (l [6] - padding, l [8] - padding, l [10] - padding)
  local max = Vector3.new (l [7] + padding, l [9] + padding, l [11] + padding)

  s = s .. max.x .. " " .. max.y .. " " .. min.z .. "\n"
  s = s .. min.x .. " " .. max.y .. " " .. min.z .. "\n"
  s = s .. min.x .. " " .. min.y .. " " .. min.z .. "\n"
  s = s .. max.x .. " " .. min.y .. " " .. min.z .. "\n"
  
  s = s .. max.x .. " " .. max.y .. " " .. max.z .. "\n"
  s = s .. min.x .. " " .. max.y .. " " .. max.z .. "\n"
  s = s .. min.x .. " " .. min.y .. " " .. max.z .. "\n"
  s = s .. max.x .. " " .. min.y .. " " .. max.z .. "\n" ..
      "c " .. Colour (colourName) .. "\n" ..
      "l 0 1\nl 1 2\nl 2 3\nl 3 0\n" ..
      "l 4 5\nl 5 6\nl 6 7\nl 7 4\n" ..
      "l 5 1\nl 0 4\nl 2 6\nl 3 7\n"
  sceneryKP (s)
end

