--[[

rob scharein
Wednesday, 10-Jan-24 18:07:27 UTC

a demo of several ways to use the chooseKP function

chooseKP let you choose from a number of options, either with
uniform probabilities or with specified relative probabilites

the function has a one, two and three argument version

to run this demo, enter either of the following into KnotPlot:
lua run chooseKP
lua do chooseKP

--]]


Demo ()

-- chooseKP has existed since KLE 5, 9 January 2023 but
-- the three argument version allowing for an arbitrary
-- separator was introduced KLE 14, 10 January 2024
-- see how this is used in Brunnian-chain.lua

RequireKLE (14)

num = 10000   -- increase this number to get better statistics

data = {}

function record (what)
  if data [what] == nil then
    data [what] = 1
  else
    data [what] = data [what] + 1
  end
end

function report ()
  echoKP (" ")
  for key, value in pairs (data) do
    echoKP (string.format ("%s: %d %.1f%%", key, value, 100.0 * value / num))
  end
  data = {}
  executeKP ("echo -f")
end

-- first two examples choose from a number of items with uniform probability

for i = 1, num do
  -- uses a space to separate items
  record (chooseKP ("cat dog yeti mouse snake"))
end
report ()

for i = 1, num do
  -- uses a comma to separate items
  record (chooseKP ("puffy cloud,tall mountain,deep blue lake"))
end
report ()

-- specify different relative probabilities
-- using the two-argument version of chooseKP

for i = 1, num do
  -- nice cats that I have known
  -- probability is proportional to how nice the cat was
  -- space separator
  record (chooseKP ("Kopek Lupin Sunshine Maggie", "444 222 888 666"))
end
report ()

for i = 1, num do
  -- comma separator
  record (chooseKP ("very small,not so big,extremely large", "4,2,1"))
end
report ()

-- three argument version of chooseKP allows for an arbitry separator

for i = 1, num do
  record (chooseKP ("red,green,blue|orange,brown|off", "1|1|20", "|"))
end
report ()



