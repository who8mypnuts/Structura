--[[

rob scharein
Friday, 2024 August 2, 18:09:37 PDT

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
  ]])

  Demo ()
  Title ("UI-demo")

  firstcall = true

end   -- end of init block

ButtonHelp ()
ButtonStack ("toggle:"
         ..  ",grid,show ~grid"
         ..  ",draw mode,lua . ToggleDrawingMode ()"
         ..  ",fullscreen,fullscreen toggle"
            )
	    
ButtonAutoHide (5, 7)


requireKPbuild (5066)


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
