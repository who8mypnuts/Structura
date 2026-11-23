luafft = require "luafft"

executeKP ([[
  %reset all
  mode cb
  %torus 3 4 128
  knot 1
  
  alias f "lua run fft"
  refine nbeads 128
  N-torus = 128
  %until once yes
  %until Ncomp 1 "torus;display true;nap .05"
]])

bead = getComponentKP (0)
size = #bead
print ("\n\nsize is " .. size)

list = {}
list.x = {}
list.y = {}
list.z = {}

for i = 1, #bead do
  list.x [i] = complex.new (bead [i].x, 0)
  list.y [i] = complex.new (bead [i].y, 0)
  list.z [i] = complex.new (bead [i].z, 0)
end


--displays a comparison of two lists with complex numbers
function compare (one, two)
  for i = 1, #one do
    print (string.format ("1: %s\t2: %s", tostring (one [i]),tostring (two [i])))
  end
end

-- divide a list with a certain constant factor
function divide (thelist, factor)
  for i, v in ipairs (thelist) do
    thelist [i] = thelist [i] / factor
  end
end

function zeroOut (thelist, threshold)
  for i, v in ipairs (thelist) do
    cn = thelist [i]
    if complex.abs (cn) < threshold then
      cn [1] = 0
      cn [2] = 0
    end
    print (i .. " k " .. cn [1] .. " " .. cn [2])
  end
end

ret = {}
ret.x = luafft.fft (list.x, false)
ret.y = luafft.fft (list.y, false)
ret.z = luafft.fft (list.z, false)

t = paramKP ("sradius")
zeroOut (ret.x, t)
zeroOut (ret.y, t)
zeroOut (ret.z, t)


--now carry out inverse fast fourier transformation and store result in "ret2"
ret2 = {}
ret2.x = luafft.fft (ret.x, true)
ret2.y = luafft.fft (ret.y, true)
ret2.z = luafft.fft (ret.z, true)

divide (ret2.x, size)
divide (ret2.y, size)
divide (ret2.z, size)



--displays a comparison of the input and the output, the real part should be equal
--the imaginary part is non zero (but fairly close) due to several calculations
--that have been carried out in the FFT
--compare (list.y, ret2.y)

for i = 1, #ret.x do
  if complex.abs (ret.x [i]) > 0.1 then
    print (i .. " x " .. ret.x [i][1] .. " " .. ret.x [i][2])
  end
  if complex.abs (ret.y [i]) > 0.1 then
    print (i .. " y " .. ret.y [i][1] .. " " .. ret.y [i][2])
  end
  if complex.abs (ret.z [i]) > 0.1 then
    print (i .. " z " .. ret.z [i][1] .. " " .. ret.z [i][2])
  end
end

newcomp = {}
local Vector3 = require ("Vector3")

for i = 1, #ret2.x do
  table.insert (newcomp,
                  Point.new (ret2.x [i][1], ret2.y [i][1], ret2.z [i][1]))
end

addComponentKP (newcomp)
--executeKP ("translate 1 0 0 1;centre")
