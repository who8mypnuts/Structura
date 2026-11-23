--[[

rob scharein
Friday, 2024 August 2, 14:31:41 PDT

--]]

UI = {}

-- mouse functions added 24 February 2023, KLE 7, KPbuild 5016
-- moved from Demos-init.lua 2 August 2024, KPbuild 5066

function UI.SetMouseFunc (functionName)
  if functionName == nil then UnsetMouse () return end
  __mouseFunc = functionName
  mouseKP ("mouse")
end

SetMouseFunc = UI.SetMouseFunc

function UI.SetMouseMotionFunc (functionName)
  if functionName == nil then UnsetMouse () return end
  __mouseMotionFunc = functionName
  mouseKP ("motion")
end

SetMouseMotionFunc = UI.SetMouseMotionFunc

function UI.SetMousePassiveMotionFunc (functionName)
  if functionName == nil then UnsetMouse () return end
  __mousePassiveMotionFunc = functionName
  mouseKP ("passive")
end

SetMousePassiveMotionFunc = UI.SetMousePassiveMotionFunc

function UI.UnsetMouse ()
  mouseKP ()
end

UnsetMouse = UI.UnsetMouse

-- keyboard functions added 19 June 2023, KLE 10, KPbuild 5025
-- moved from Demos-init.lua 2 August 2024, KPbuild 5066

function UI.SetKeyboardFunc (functionName)
  if functionName == nil then UnsetKeyboard () return end

  __keyboardFunc = functionName
  keyboardKP ("keyboard")
end

SetKeyboardFunc = UI.SetKeyboardFunc

function UI.UnsetKeyboard ()
  keyboardKP ()
end

UnsetKeyboard = UI.UnsetKeyboard

UI.origin = lcaptureKP ("vpproject 0 0 0")
UI.winz = UI.origin [3]
function UI.WindowToWorld (winx, winy, winz)
  if winz == nil then
    winz = UI.winz
  end
  local com = "vpunproject " .. winx .. " " .. winy .. " " .. winz
  local s = lcaptureKP (com)
  return s [1], s [2], s [3]
end

local orthoMouseDown = nil
local orthoMouseUp = nil

local function orthoMouse (winx, winy, button, mouseUp)
  if button > 0 then
    return false
  end
  
  if mouseUp then
    executeKP ("untran;ortho")
    if orthoMouseUp then
      orthoMouseUp ()
    end
  else
    executeKP ("persp")
    if orthoMouseDown then
      orthoMouseDown ()
    end
  end
  executeKP ("display true")
  return false
end


function UI.orthoMouse (down, up)
  orthoMouseDown = down
  orthoMouseUp = up
  UI.SetMouseFunc (orthoMouse)
end

-- added 11 September 2024
-- not sure why UI.resizeCallback doesn't work
-- lua_getglobal doesn't find it

UI.topMenu = {}
UI.currentTab = 0
UI__topMenuCallbacks = {}

function UI_topMenuCallback (which)
  if UI.currentTab == which then
    echoKP ("ignoring")
    return
  end
  --echoKP ("which is " .. which)
  UI.currentTab = which
  local windowInfo = mlcaptureKP ("winfo")
  UI_resizeCallback (string.sub (windowInfo [2][7], 2, -2),
                     string.sub (windowInfo [2][8], 1, -3))
  
   UI__topMenuCallbacks [which] ()
end

function UI_resizeCallback (width, height)
  --print (width, height)
  local padding = ' '
  local left =  padding
  local right = padding
  local button
  local widthButton
  local xincr = width / #UI.topMenu
  local x = xincr / 2.0
  local y = 20
  
  executeKP ([[
    txt delete group topMenu
    txt push
    txt group topMenu  % made group names a string, not an int, 19 September 2024
    txt fill off
    txt font 4
    txt centre
    vpshow draw
    txt fill on
    txt fcolour white 0
    vpshow colour white
  ]])
  

  local com
  local menubot = 28
  local inset = 5
  
  start_end = {}
  table.insert (start_end, {0,0})

  for i = 1, #UI.topMenu do
    button = UI.topMenu [i]
    paddedButton = padding .. button .. padding
    extra = '  '
    widthButton = captureKP ('txt phantom "' .. extra .. paddedButton .. extra ..'" ?')
    
    --print (button, widthButton)
    local xstart = x - widthButton / 2
    local xend = xstart + widthButton
    local xleft = xstart + inset
    local xright = xend - inset
    local menutop = 3
    if i == UI.currentTab then
      com = "moveto"
    else
      com = "lineto"
    end
    
    table.insert (start_end, {xstart, xend})
    
    --         1  2  3       4       5     6        7      8       9        10 11   12
    executeKP (x, y, button, xstart, xend, menubot, xleft, xright, menutop, i, com, paddedButton, [[
      txt phantom "ARG12"
      txt ARG1 -ARG2 "ARG3" "lua . UI_topMenuCallback (ARG10)"
      vpshow moveto "<ARG4" ">ARG6"
      vpshow ARG11  "<ARG5" ">ARG6"
      vpshow lineto "<ARG8" ">ARG9"
      vpshow lineto "<ARG7" ">ARG9"
      vpshow lineto "<ARG4" ">ARG6"
    ]])
    x = x + xincr
  end
  
  table.insert (start_end, {width,width})

  for s = 2, #start_end do
    executeKP (start_end [s - 1][2], start_end [s][1], menubot, [[
      vpshow moveto "<ARG1" ">ARG3"
      vpshow lineto "<ARG2" ">ARG3"
    ]])
  end

  executeKP ([[
    txt pop
  ]])
end


function UI.topMenuInit (items, callbacks)
  if #items ~= #callbacks then return end
  executeKP ([[
    lua resize UI_resizeCallback
  ]])
  UI.topMenu = items
  UI__topMenuCallbacks = callbacks
  UI.currentTab = RollDie (#callbacks)
  
  local windowInfo = mlcaptureKP ("winfo")
  UI_resizeCallback (string.sub (windowInfo [2][7], 2, -2),
                     string.sub (windowInfo [2][8], 1, -3))

end

function UI.trim(s)  -- trims blanks from both ends of a string
  local l = 1
  while strsub(s,l,l) == ' ' do
    l = l+1
  end
  local r = strlen(s)
  while strsub(s,r,r) == ' ' do
    r = r-1
  end
  return strsub(s,l,r)
end

return UI

