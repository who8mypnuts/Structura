--[[

  4 March 2023
  test the no-upper-limit to number of arguments
  
--]]
Demo ()
RequireKLE (8)

executeKP (
  "6.3",      -- 1
  "10.102",   -- 2
  "Burnt",    -- 3
  'azure',    -- 4
  "monolith", -- 5
  "grid",     -- 6
  "axes",     -- 7
  102,        -- 8
  0,          -- 9
  9.25,       -- 10
  1.5,        -- 11
  "sum",      -- 12
  0.34,       -- 13
  "centre",   -- 14
  -22,        -- 15
  47,         -- 16
  4,          -- 17
  "c",        -- 18
  "A Test",   -- 19
  -20,        -- 20
  "writhe",   -- 21
  22,         -- 22
  1.3,        -- 23
  0.234,      -- 24
  0.09,       -- 25
  3,          -- 26
  "z",        -- 27
  54,         -- 28
  "dk3dgD",   -- 29
  5,          -- 30
  -7,         -- 31
  5,          -- 32
  3,          -- 33
  
  [[
  reset all
  rotate y ARG16
  txt init
  txt ARG14
  load ARG1
  vscale = ARG24
  rotate i ARG15
  background = rgbi:0/0/ARG28
  txt font ARG17
  load ARG12 ARG2
  scenery on
  txt ARG18 ARG20 "ARG19"
  scenery vscale ARG11
  scenery object eobj/ARG5 0 ARG10 0
  show ARG6 ARG7
  go ARG8
  scenery vscale ARG33
  scenery object eobj/ARG29 ARG30 ARG31 ARG32
  stusplit = 1
  sradius = ARG13
  load combine zero-ARG21-tref.k
  refine equi ARG23
  translate ARG22 0 0 1
  safe
  colour 0 ARG3Orange
  colour 1 ARG4
  tfunction ARG26 "idle ~rotate;txt on"
  alias ~rotate "rotate ARG27 ARG25"
  ]]
)


SetMouseFunc (function (a, b, c, d) executeKP ("idle") return false end)

