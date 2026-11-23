--[[

rob scharein, 21 june 2023
in the Public Domain

--]]

Lsystem = {}

Lsystem.callback = nil
Lsystem.current = nil

-- an L-system function name should
-- start with an uppercase letter

function Lsystem.Peano (order)
  if order < 0 then
    return {"Peano", 2, 3, 1, 4}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("Peano Curve", order)
  end
  Lsystem.current = Lsystem.Peano
  executeKP (order, [[
    lsystem init
    lsystem axiom X
    lsystem X XFYFX+F+YFXFY-F-XFYFX
    lsystem Y YFXFY-F-XFYFX+F+YFXFY
    lsystem delta 90
    lsystem ARG1
  ]])
end

-- https://people.ece.cornell.edu/land/OldStudentProjects/cs490-94to95/hwchen/
function Lsystem.tree (order)  -- not working
  if order < 0 then
    return {"Tree", 2, 3, 0, 7}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("Tree", order)
  end
  Lsystem.current = Lsystem.Tree
  executeKP (order, [[
    lsystem init
    lsystem axiom F
    lsystem F [- & < F][ < + + & F ] | | F [ - - & > F ] [+ & F ]
    lsystem delta 22.5
    lsystem ARG1
  ]])
end


function Lsystem.Hilbert (order)
  if order < 0 then
    return {"Hilbert", 4, 5, 1, 6}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("Hilbert Curve", order)
  end
  Lsystem.current = Lsystem.Hilbert
  executeKP (order, [[
    lsystem init
    lsystem axiom X
    lsystem X -YF+XFX+FY-
    lsystem Y +XF-YFY-FX+
    lsystem delta 90
    lsystem ARG1
  ]])
end

-- https://math.stackexchange.com/questions/123642/representing-a-3d-hilbert-curve-as-an-l-system
  
function Lsystem.Hilbert3D (order)
  if order < 0 then
    return {"Hilbert3D", 2, 2, 1, 4}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("3D Hilbert Curve!", order)
  end

  Lsystem.current = Lsystem.Hilbert3D
  executeKP (order, [[
    lsystem init
    lsystem axiom X
    lsystem X ^<XF^<XFX-F^>>XFX&F+>>XFX-F>X->
    lsystem delta 90
    lsystem ARG1
  ]])
end

function Lsystem.Koch (order)
  if order < 0 then
    return {"Koch", 0, 3, 0, 6}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("Koch Curve", order)
  end
  Lsystem.current = Lsystem.Koch
  executeKP (order, [[
    lsystem init
    lsystem axiom F--F--F
    lsystem F F + F -- F + F
    lsystem ARG1
  ]])
end

function Lsystem.TDragon (order)
  if order < 0 then
    return {"TDragon", 3, 9, 0, 14}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("TDragon", order)
  end
  Lsystem.current = Lsystem.TDragon
  executeKP (order, [[
    lsystem init
    lsystem delta 90
    lsystem alpha 45
    lsystem axiom Fb
    lsystem  b b+jF+
    lsystem  j -Fb-j
    lsystem ARG1
  ]])
end


function Lsystem.Squiggle (order)
  if order < 0 then
    return {"Squiggle", 3, 4, 0, 6}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("Squiggle Curve", order)
  end
  Lsystem.current = Lsystem.Squiggle
  executeKP (order, [[
    lsystem init
    lsystem axiom F+XF+F+XF
    lsystem X XF-F+F-XF+F+XF-F+F-X
    lsystem delta 90
    lsystem ARG1
  ]])
end

function Lsystem.QKoch (order)
  if order < 0 then
    return {"QKoch", 1, 2, 0, 3}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("Quadratic Koch Curve", order)
  end
  Lsystem.current = Lsystem.QKoch
  executeKP (order, [[
    lsystem init
    lsystem delta 90
    lsystem axiom F-F-F-F
    lsystem F F+FF-FF-F-F+F+FF-F-F+F+FF+FF-F
    lsystem ARG1
  ]])
end

function Lsystem.Islands (order)
  if order < 0 then
    return {"Islands", 1, 2, 0, 2}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("Islands", order)
  end
  Lsystem.current = Lsystem.Islands
  executeKP (order, [[
    lsystem init
    lsystem init
    lsystem delta 90
    lsystem alpha 0
    lsystem axiom F-F-F-F
    lsystem F F-f+FF-F-FF-Ff-FF+f-FF+F+FF+Ff+FFF
    lsystem f ffffff

    lsystem ARG1
  ]])
end

function Lsystem.Gosper (order)
  if order < 0 then
    return {"Gosper", 1, 4, 1, 5}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("Gosper Curve", order)
  end
  Lsystem.current = Lsystem.Gosper
  executeKP (order, [[
    lsystem init
    lsystem axiom XF
    lsystem X X+YF++YF-FX--FXFX-YF+
    lsystem Y -FX+YFYF++YF+FX--FX-Y
    lsystem delta 60
    lsystem alpha 0

    lsystem ARG1
  ]])
end


function Lsystem.QGosper (order)
  if order < 0 then
    return {"QGosper", 1, 2, 0, 3}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("Quadratic Gosper Curve", order)
  end
  Lsystem.current = Lsystem.QGosper
  executeKP (order, [[
    lsystem init
    lsystem delta 90
    lsystem alpha 0
    lsystem axiom G
    lsystem F FF-G-G+F+F-G-GF+G+FFG-F+G+FF+G-FG-G-F+F+GG-
    lsystem G +FF-G-G+F+FG+F-GG-F-G+FGG-F-GF+F+G-G-F+F+GG

    lsystem ARG1
  ]])
end


function Lsystem.Gasket (order)
  if order < 0 then
    return {"Gasket", 1, 6, 1, 9}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("Sierpinski Gasket", order)
  end
  Lsystem.current = Lsystem.Gasket
  executeKP (order, [[
    lsystem init
    lsystem axiom G
    lsystem F G+F+G
    lsystem G F-G-F
    lsystem delta 60
    lsystem alpha 180

    lsystem ARG1
  ]])
end

function Lsystem.Dragon (order)
  if order < 0 then
    return {"Dragon", 2, 6, 0, 14}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("Dragon", order)
  end
  Lsystem.current = Lsystem.Dragon
  executeKP (order, [[
    lsystem init
    lsys axiom F
    lsys F F+G+
    lsys G -F-G
    lsys delta 90

    lsystem ARG1
  ]])
end


function Lsystem.DrP17a (order)
  if order < 0 then
    return {"DrP17a", 1, 4, 1, 4}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("DrP17a", order)
  end
  Lsystem.current = Lsystem.DrP17a
  executeKP (order, [[
    lsystem init
    lsys axiom -L
    lsys delta 90
    lsys alpha 270

    lsys L LF+RFR+FL-F-LFLFL-FRFR+
    lsys R -LFLF+RFRFR+F+RF-LFL-FR
    lsystem ARG1
  ]])
end

function Lsystem.DrP17b (order)
  if order < 0 then
    return {"DrP17b", 1, 3, 1, 3}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("DrP17b", order)
  end
  Lsystem.current = Lsystem.DrP17b
  executeKP (order, [[
    lsystem init
    lsys axiom -L
    lsys delta 90
    lsys alpha 270

    lsys L LFLF+RFR+FLFL-FRF-LFL-FR+F+RF-LFL-FRFRFR+
    lsys R -LFLFLF+RFR+FL-F-LF+RFR+FLF+RFRF-LFL-FRFR

    lsystem ARG1
  ]])
end


function Lsystem.Birch (order)
  if order < 0 then
    return {"Birch", 1, 3, 0, 4}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("Birch Tree", order)
  end
  Lsystem.current = Lsystem.Birch
  executeKP (order, [[
    lsystem init
    lsys delta 22.5

    lsys axiom F
    lsys F FF+[+F-F-F]-[-F+F+F]

    lsystem ARG1
  ]])
end

function Lsystem.Pine (order)
  if order < 0 then
    return {"Pine", 5, 9, 0, 11}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("Pine Tree", order)
  end
  Lsystem.current = Lsystem.Pine
  executeKP (order, [[
    lsystem init
    lsys delta 22.5

    lsys delta 18
    lsys axiom XKFFF
    lsys X [---G][+++G]TX
    lsys G +H[-G]K
    lsys H -G[+H]K
    lsys T TK
    lsys K [-FFF][+FFF]F

    lsystem ARG1
  ]])
end


function Lsystem.NestedTri (order)
  if order < 0 then
    return {"NestedTri", 1, 5, 0, 6}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("Nested Triangles", order)
  end
  Lsystem.current = Lsystem.NestedTri
  executeKP (order, [[
    lsystem init
    lsys delta 60
    lsys alpha 0
    lsys axiom F--F--F
    lsys F F[--F++F]F
    lsystem ARG1
  ]])
end


function Lsystem.template (order)
  if order < 0 then
    return {"template", 1, 6, 1, 9}
  end
  if Lsystem.callback ~= nil then
    Lsystem.callback ("template", order)
  end
  Lsystem.current = Lsystem.template
  executeKP (order, [[
    lsystem init
    
    lsystem ARG1
  ]])
end

function Lsystem.defined (sorted)
  if sorted == nil then sorted = true end  -- sorting added 18 February 2025, KPbuild 5090
  
  -- return a table of defined L-systems
  -- https://www.lua.org/pil/19.3.html
  
  local sys = {}
  for key, value in pairs (Lsystem) do
    if type (type (value) == "function") then
      local f = string.sub (key, 1, 1)
      if string.upper (f) == f then
        table.insert (sys, value)
      end
    end
  end
  if sorted then
    table.sort (sys, function (l1, l2)
                       return l1(-1)[1] < l2(-1)[1]  -- sort by name
                     end
               )
  end
  return sys
end


-- support for old stuff: RULD curves

local ruld = {}
ruld ["R"] = "E" ruld ["U"] = "N" ruld ["L"] = "W" ruld ["D"] = "S"
ruld ["r"] = "e" ruld ["u"] = "n" ruld ["l"] = "w" ruld ["d"] = "s"

function RULD (s)
  local t = ""
  for i = 1, #s do
    local c = string.sub (s, i, i)
    t = t .. ruld [c]
  end
  return t
end
