--[[

rob scharein, 7 march 2023

--]]

if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    txt centre
    txt font 3
    sformat = 1
    vscale = 0.102
    alias -e lor "lua . Lorenz ({$0})"
    txt fill on
    txt font 4
    txt lineskip 39
    txt left
    txt 15 -33 xy "lua . Lorenz('xy')"
    txt 15 a xxy "lua . Lorenz('xxy')"
    txt 15 a  yyx "lua .  Lorenz('yyx')"
    txt 15 a  xyx,yyxy "lua .  Lorenz('xyx,yyxy')"
    txt 15 a  xxy,xy,xyy "lua .  Lorenz('xxy,xy,xyy')"
    txt 15 a  xxy,xy,yyx,xxyy "lua .  Lorenz('xxy,xy,yyx,xxyy')"
   
    vscale = .097
  ]])
  
  Demo ()
  Title ("Lorenz Knots and Links")

end

function Lorenz1 (words)
  local word = explode (",", words)

  -- check for valid words
  for i = 1, #word do
    if #word [i] < 1 then
      echoKP ("*** word of zero length found")
      return 0,0,0,0
    end
    for j = 1, #word [i] do
      if not (charAt (word [i], j) == 'x' or charAt (word [i], j) == 'y') then
        echoKP ("*** invalid character `" .. charAt (word [i], j) .. "'")
        return 0,0,0,0
      end
    end
  end
  

  local maxlength = 0
  local nlines = 0
  local N = 1
  local length = {}
  for i = 1, #word do
    length [i] = #word [i]
    N = lcm (N, length [i])
    nlines = nlines + length [i]
    if length [i] > maxlength then
      maxlength = length [i]
    end
  end
  
  n = 0
  local stuffT = {}
  
  for i = 1, #word do
    for offset = 0, length [i] - 1 do
      stuff = ""
      for k = 0, N - 1 do
        stuff = stuff .. charAt (word [i], (k + offset) % length [i] + 1)
      end
      
      stuff = stuff .. " " ..
              charAt (word [i], offset % length [i] + 1) .. " " ..
              offset .. " " .. (offset + 1) % length [i] .. " " ..
              n * maxlength + offset .. " " ..
              n * maxlength + (offset + 1) % length [i]
      table.insert (stuffT, stuff)
    end
  
    n = n + 1
  end
  
  table.sort (stuffT)
  return nlines, #word, maxlength, stuffT
end

function pt (t, n)
  print (n .. ":")
  for k, v in ipairs (t) do
    print (k .. " " .. v)
  end
end

function Lorenz (words)
  Title (words)
  
  nlines, nknots, maxlength, lines = Lorenz1 (words)
  if nknots == 0 then return end
  
  local nbeads = 36
  local xmin = -9.99 local xmax = 9.99
  local ymin = -10.0 local ymax = 10.0
  local firsty = -1
  local yinc = (ymax - ymin) / (nlines + 1)
  local y = ymin + yinc
  
  local kps = "delete all\nnew = false\nline num " .. nbeads .. "\n\n"
  
  local beginpoint = {}
  local endpoint = {}
  local loc = {}

  for i = 1, nlines do
    local word = explode (" ", lines [i])
    local branch = word [2]
    local fromm = tonumber (word [3])
    local too = tonumber (word [4])
    local from = tonumber (word [5])
    local to = tonumber (word [6])
    beginpoint [i] = from
    endpoint [i] = to
    loc [from] = y
    if branch == "y" and firsty == -1 then firsty = i end
    y = y + yinc
  end
  
  --pt (beginpoint, "begpo")
  --pt (endpoint, "endpo")
  --pt (loc, "loc")
  --print ("firsty " .. firsty)

  function lineFromTo (fx, fy, fz, tx, ty, tz)
    return "line from " ..
          string.format ("%.3f", fx) .. " " ..
          string.format ("%.3f", fy) .. " " ..
          string.format ("%.3f", fz) .. " " ..
          " to " ..
          string.format ("%.3f", tx) .. " " ..
          string.format ("%.3f", ty) .. " " ..
          string.format ("%.3f", tz) .. " " .. "\n"
    end


  kps = kps .. "\n\n%% x-branch\n\n"

  i = 2
  for i = 1, firsty - 1 do
    kps = kps .. lineFromTo (xmin, loc [beginpoint [i]], 0,
                             xmax, loc [endpoint [i]], 0)
  end
  
  kps = kps ..  "scale .05 .05 .05\ntranslate .5 .5 0\nwarp xlorenz\n" ..
                "save .x-branch\ndelete all\n";
  

  kps = kps .. "\n\n%% y-branch\n\n"
   i = 7
  for i = firsty, nlines do
    kps = kps .. lineFromTo (xmin, loc [beginpoint [i]], 0,
                             xmax, loc [endpoint [i]], 0)
  end
  
  kps = kps ..  "scale .05 .05 .05\ntranslate .5 .5 0\nwarp ylorenz\n" ..
                "save .y-branch\n";
  kps = kps .. "load comb .x-branch\n"
  executeKP (kps)
  Finish (words)
end

function Finish (words)
  executeKP (words, [[
    scale 4
    join all
    ago 33
    scale 1 1 2
    meta -info
    safe
    meta words "ARG1"
  ]])
end




print ("number is " .. #arg)
if #arg == 0 then
  Lorenz ('xy')
else
  local l = ""
  for i = 1, #arg do
    if i > 1 then l = l .. "," end
    l = l .. arg [i]
  end
  Lorenz (l)
end
