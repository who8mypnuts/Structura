--[[

rob scharein
Saturday, 2024 July 20, 12:59:27 PDT

--]]

if #arg ~= 1 then
  max = 1
else
  max = arg [1]  -- references to arg should come before the call to Demo ()
                 -- because calling Demo () resets the value of arg to nil
end

if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    vscale = 0.1
    alias cl "lua . close ('$0')"
    say -on
  ]])

  Demo ()
  Title ("braids")

  firstcall = true
  
  require ("KnotTheory")
  braidsLength = KnotTheory.braidsLength
  
end   -- end of init block

ButtonHelp ()

if not requireKPbuild (5065) then
  EphemeralMessage ("needs an update to KnotPlot")
  executeKP ([[
    display true
    panic needs an update to KnotPlot
  ]])
end


if firstcall then
  firstcall = false
end

executeKP (max, [[
  timer start
  gauss open bARG1
]])

function close (word)
  local prefix = ""
  if #word < 4 then
    -- add a prefix if the word is short, otherwise
    -- the warping might produce a bad embedding
    prefix = "0^4 "
  end
  executeKP (prefix, word, [[
    echo braid -strings 3 ARG1ARG2
    braid -strings 3 ARG1ARG2
    warp rec2ann 1  % warp rectangle to annulus with gap of 1
    join all
    about z 90      % look nicer :-)
    if ncomp == 1 then "ago 5"           % relax a bit to bring into general position
    if ncomp == 1 then gauss
    echo -f
  ]])
end

for n = 1, max do
  braids = braidsLength (n)
  Title ("Length " .. n)
  for b = 1, #braids do
    SubTitle (b .. " of " .. #braids)
    BotTitle (braids [b])
    close (braids [b])
  end
  executeKP (n, [[
    say ARG1
  ]])
end

executeKP ([[
  gauss close
  timer check
  say I am all done
]])


--[[

BEGIN HELP
some helpful text should go here...


change this to an interactive demo that can still be run in non-graphics mode




some helpful text should go here...
END HELP

6
57 seconds

7
4.7 minutes

8
19 minutes
27 minutes

8 knots only
10.4 minutes

9 knots only
11.7 minutes

10
8.8 hours

--]]
