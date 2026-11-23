--[[

rob scharein, 12 august 2023

reimplementation of split-delete.kps

--]]


if demo ~= luaSource then
  --demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    alias ~ah "txt hide \rr[5/7]"
    mode cb
    
    cradius = 0.15
    sradius = 0.4
    bradius = 0.21
    vscale = 0.3
    dbmin = 5
    
    %alias ~newknot "idle;go 0;~setname;txt delete hint;drag=f;par3=0;txt delete group 102;untran;save |.tmp;<split-delete-aux2.kps"
    alias -e newknot "lua . NewKnot ()"

    
    function init
    function silent
    function 2 "www knotplot.com/thesis"

  ]])

  Demo ()
  Title ("Simplify Knot Embeddings")
  SubTitle ("using split/delete and dynamics")

end   -- end of init block

function SetName ()
  executeKP (captureKP ("name"), [[
    ~ah
    txt push
    txt font 4
    txt left
    txt fill off
    txt 10 -20 "ARG1"
    txt pop
  ]])
end


function Aux1 ()
  executeKP ([[
    % 4 June 2002, Rob Scharein
    stusplit = \ri[3/7]
    idle "ago \ri[2/20];delete downto -4"
    #3 echo
    txt delete group 111
    txt lineskip 30
    txt clobber on
    if \ppar3 == 1 then "txt right;txt -20 c hint <split-delete-hint.kps"
    txt font 3
    txt centre
    txt fill on
    txt lineskip 30
    txt push
    txt group 111
    txt c 80 "delete many beads" ~delmany
    txt c 50 "reload last knot" "load |.tmp;read split-delete-aux2.kps"
    txt c 20 "relax normally"   ~relaxnorm
    txt pop
    dbfail=22
  ]])
end

function Aux2 ()
  executeKP ([[
    txt delete group 111
    go 0
    par0=\rr[1/22]
    nop \t0
    idle

    txt delete hint
    drag = false

    txt font 3
    txt centre
    txt fill on
    txt lineskip 30
    txt push
    txt group 111
    %txt c 50 "begin simplification" "txt delete Evalu;<split-delete-aux.kps"
    txt pop
    txt on
  ]])

end

function NewKnot ()
  executeKP ([[
    idle
    go 0
    txt delete hint
    drag = false
    par3=0
    txt delete group 102
    untran
    save |x
  ]])
  SetName ()
  Aux2 ()
  Title (" ")
  SubTitle (Plural (tonumber (captureKP ("xing")), "crossing"))
end


creditedLou = false

function ContinuedFractionUnknot ()
  local tanglePadding = 3
  if not creditedLou then
    creditedLou = true
    executeKP (tanglePadding, [[
      #4 echo
      echo idea for this example from Lou Kauffman
      %echo using a tangle padding of ARG1
      echo
    ]])
  end
  
  executeKP (tanglePadding, [[
    tangle push
    tg1offset = ARG1
    echo -n "turning "
    tangle padding on
  ]])
  
  executeKP (Random ("ri[-5/5]"),
             Random ("ri[-5/5]"),
             Random ("ri[-5/5]"),
             Random ("ri[-5/5]"), [[
    echo making tangle...
    tangle (ARG1,ARG2,ARG3,ARG4)(ARG1,ARG2,ARG3)z#
    name "tangle (ARG1,ARG2,ARG3,ARG4)(ARG1,ARG2,ARG3)z#   <--- numbers are randomly chosen (click again)"
    ago 33
    tangle pop
    echo -n "turning "
    tangle padding
 ]])
 
 NewKnot ()
end

function ToggleDrawingMode ()
  if captureKP ("mode") == "mode s" then
    executeKP ("mode cb")
  else
    executeKP ("mode s")
  end
end
