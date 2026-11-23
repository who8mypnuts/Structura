-- Example Lua Script for a KnotPlot demo
-- Rob Scharein, 21 March 2022

Demo ()            -- defines Title() and so on, see Demos-init.lua

z = -10
first = true

-- can execute a block of KnotPlot commands at a time using a Lua long string

executeKP ([[
reset all
cyl-rad = 0.119
silent = true
mode cb
background = darkblue
txt clobber on
]])

Title ("A New Construction")
BotTitle ("made using the Lua extension (added 21 March 2022)")


repeat
  executeKP ("unknot 200 10")
  latitude = 8 * z * math.pi / 180
  executeKP ("scale " .. math.cos (latitude))
  executeKP ("translate 0 0 " .. z)
  executeKP ("refine equilateral 1")
  if not first then
    executeKP ("load comb |x")
  end
  executeKP ("save |x")
  
  z = z + 1
  first = false
until (z > 10)

executeKP ([[
silent = false
length
#3 echo
echo Lua now embedded in KnotPlot!
echo more info coming soon...
tanforce = on
alias ~mf "lua . MoreFun ()"
tfunc \rr[5/9] "cut span x 0;revbeads random;tfunc \rr[1/4] ~mf"
]])

function MoreFun ()
  executeKP ([[
    go
    txt delete made
  ]])
end

ShowSourceButton ()

