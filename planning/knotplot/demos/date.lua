--[[

rob scharein
Monday, 2024 September 2, 15:59:11 PDT

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    ortho
    sradius = 0.11
    vscale = 0.237
    mode sE
    tess colour blue
    background = black
  ]])

  Demo ()
  Title ("date")

  BotButton ("rerun", "lua rerun")
  firstcall = true

end   -- end of init block

ButtonHelp ()
ButtonStack ("toggle:"
         ..  ",grid,show ~grid"
         ..  ",draw mode,lua . ToggleDrawingMode ()"
         ..  ",fullscreen,fullscreen toggle"
            )
	    


option = explode (',', ',-u,"%M","%H",-u "%H","%A %e %B %Y %H %M %S %Z"')
for i = 1, #option do
  com = 'date ' .. option [i]
  echoKP (com)
  echoKP (captureKP (com))
end


--executeKP ("load nlor/lor-fe.k")
executeKP ("knot newcd")

cd = captureKP ("meta -v CreationDate")
now = captureKP ("date -u iso")
sbd = captureKP ('util sbd "' .. cd .. '" "' .. now .. '"')
ftime = captureKP ('util ftime ' .. sbd)
EphemeralMessage (cd, now, sbd, ftime)
  
noon = "2024   9  2    12 0   0"
nowPDT = captureKP ("date iso")

sbd = captureKP ('util sbd "' .. noon .. '" "' .. nowPDT .. '"')
echoKP (captureKP ('util ftime ' .. sbd) .. ' since noon today')

bd = "1959 10 22 12 33 0 0"
sbd = captureKP ('util sbd "' .. bd .. '" "' .. nowPDT .. '"')
echoKP (sbd)
echoKP (captureKP ('util ftime ' .. sbd))

requireKPbuild (5069)


if firstcall then
  firstcall = false
end


--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
