--[[

rob scharein
Tuesday, 2024 October 1, 09:15:14 PDT

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    mode cb
    show axes
    sradius = 0.15
    alias ~loadseq "lua . loadSequence ('$0')"
  ]])

  Demo ()
  Title ("lnknum, acn, writhe")

  BotButton ("rerun", "lua rerun")
  
  firstcall = true

end   -- end of init block

ButtonHelp ()
ButtonStack ("toggle:"
         ..  ",grid,show ~grid"
         ..  ",axes,show ~axes"
         ..  ",centring,lua . toggleCentring ()"
         ..  ",draw mode,lua . ToggleDrawingMode ()"
         ..  ",fullscreen,fullscreen toggle"
            )
            
ButtonStack ("compute:"
         ..  ",acn,acn"
         ..  ",writhe,writhe"
         ..  ",lnknum,lnknum"
         ..  ",xing,xing"
         )
         
ButtonStack ("action:"
         ..  ",next,lua . next()"
         ..  ",ago 5,ago 5"
         ..  ",centre,centre"
         ..  ",delete,delete downto 0"
         ..  ",align,align axes legacy"
         )
         
ButtonStack ("rotate:"
         ..  ",xz,rotate xz"
         ..  ",yx,rotate yx"
         ..  ",view,rotate xz;rotate i 32;rotate j 10"
         )

ButtonStack ("left")
-- the following line is needed, this is a bit of a hack
-- this will be fixed and you won't have to do this
executeKP ('txt push;txt fill off;txt 15 .01 " ";txt pop')

ButtonStack ("select on,group seq|sequence:"
  -- run the following command in the special directory:
         ..  ",2x1-20,~loadseq  2x1-20.b"
         ..  ",2x1-40,~loadseq  2x1-40.b"
         ..  ",2x1-60,~loadseq  2x1-60.b"
         ..  ",2x1-80,~loadseq  2x1-80.b"
         ..  ",3x1-100-ham,~loadseq  3x1-100-ham.b"
         ..  ",3x1-20-ham,~loadseq  3x1-20-ham.b"
         ..  ",3x1-20,~loadseq  3x1-20.b"
         ..  ",3x1-40-ham,~loadseq  3x1-40-ham.b"
         ..  ",3x1-40,~loadseq  3x1-40.b"
         ..  ",3x1-60-ham,~loadseq  3x1-60-ham.b"
         ..  ",3x1-60,~loadseq  3x1-60.b"
         ..  ",3x1-80-ham,~loadseq  3x1-80-ham.b"
         ..  ",3x1-80,~loadseq  3x1-80.b"
         ..  ",4x1-20,~loadseq  4x1-20.b"
         ..  ",4x1-40,~loadseq  4x1-40.b"
         ..  ",4x1-60,~loadseq  4x1-60.b"
         ..  ",4x1-80,~loadseq  4x1-80.b"
)

centring = false
function toggleCentring ()
  centring = not centring
  executeKP (tostring (centring), [[
    echo auto-centring is ARG1
  ]])
end
toggleCentring ()

function centre ()
  if centring then
    executeKP ("centre")
  end
end

function loadSequence (seq)
  Title (string.sub (seq, 1, -3))
  executeKP (seq, [[
    sequence 2sap ARG1
  ]])
  centre ()
end


function next ()
  executeKP ([[
    sequence +
  ]])
  centre ()
end

requireKPbuild (5074)


if firstcall then
  firstcall = false
  executeKP ([[
    txt click view
    txt click 2x1-20
  ]])
end


--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
