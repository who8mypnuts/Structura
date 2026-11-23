
if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    load nasty1.k
    tholder install s
    load nasty2.k
    tholder install t
    delete all
    ortho
    txt init
    txt font 4
    txt centre
    txt fill on
    txt clobber on
    vscale = 0.08
  ]])
  Demo ()
  Title ("Knot Mutants")
  BotButton ("create", "lua . Create ()")
end

function Create ()
  local tc = ""
  local label = ""
  local space = ""
  local spacing = 4;
  
  for i = 1, 9 do
    op = chooseKP ("1 3 1z 3z $ $z $@ $@z i 0")
    --op = chooseKP ("1 3")
    tc = tc .. op
    if i == 4 or i == 7 then label = "    " .. label end
    label = op .. space .. label
    space = "  "
  end
  
  print (">>" .. label .. "<<")
  
  executeKP (tc, label, spacing, [[
    Drawing = false
    txt fill off
    txt font 4
    txt c 40 "substituted: ARG2"
    tangle ARG1s
    echo tangle ARG1s
    meta tangle ARG1s
    ago 44
    translate maxx to -ARG3
    save |l
    save |a
    tangle ARG1t
    ago 44
    translate minx to ARG3
    save |r
    save |b
    Drawing = true
    load |l
    load combine |r
    save |combo
  ]])
  
  
  hl = FLYPMOTH ("l", label, tc .. "s")

  hr = FLYPMOTH ("r", label, tc .. "t")

  print ("----")
  print (label)
  print (hl)
  print (" ")
  print (hr)
  if hr ~= hl then
    same = "differ"
  else
    same = "same"
  end
  executeKP (hl, hr, same, [[
    txt push
    txt c 110 "homflys ARG3"
    txt left
    txt font 2
    %txt 10 87 "ARG1"
    %txt 10 70 "ARG2"
    load |combo
    txt pop
  ]])
  
end

function FLYPMOTH (knot, label, tc)
  executeKP (knot, label, tc, [[
    load |ARG1
    centre
    meta -info
    meta tangle "tangle ARG3"
    meta insert "ARG2"
    save |ARG1
    save ARG1.k
    meta -init
  ]])
  local egc = captureKP ("gauss")
  return osx ("echo '" .. egc .. "' | jhomfly --")
end

--[[

121112111

2 2 1 1 1 2 1 1 2 seems to give different homflys
2 1 1 1 1 1 2 1 1

--]]

