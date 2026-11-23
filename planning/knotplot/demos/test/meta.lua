--[[

rob scharein
Monday, 2024 August 19, 19:38:44 PDT

this tests the Utilities.meta () function

--]]


require "Utilities"

print ('\n\n\n')

executeKP (chooseKP ('torus,weird thing,twist,unknown and complex entity', '1,1,1,1'), [[
  knot newcd
  meta "knot family" "ARG1"
  meta "a key with a : in it" "and a value"
  meta "some key" "but the value contains the : character"
  meta
]])

meta = Utilities.meta ()

print ("symmetry is >" .. meta ['symmetry'] .. '<')
print ("Creator is >" .. meta ['Creator'] .. '<')
print ("CreationDate is >" .. meta ['CreationDate'] .. '<')
print ("knot family is >" .. meta ['knot family'] .. '<')
print ("weird meta 1 is >" .. meta ['a key with a '] .. '<')
print ("weird meta 2 is >" .. meta ['some key'] .. '<')

print ('\n\n')

executeKP ([[
  knot
  meta
]])


meta = Utilities.meta ()
if meta == nil then
  print (captureKP ('util last') .. ' has no metas')
end

print ('\n\n')

executeKP ([[
  load tri-spiral.k
  meta
]])

meta = Utilities.meta ()

for k,v in pairs (meta) do
  print ('>' .. k .. '<>' .. v .. '<')
end
