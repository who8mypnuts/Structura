--[[

rob scharein
Wednesday, 2024 September 11, 19:19:50 PDT

--]]


if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    txt on
    txt clobber on
    background = Lupin
  ]])

  Demo ()

  firstcall = true
  
  require "UI"
  
  BotButton ("rerun", "lua rerun")

end   -- end of init block

ButtonHelp ()
ButtonStack ("toggle:"
         ..  ",grid,show ~grid"
         ..  ",draw mode,lua . ToggleDrawingMode ()"
         ..  ",fullscreen,fullscreen toggle"
            )
	    
--ButtonAutoHide (5, 7)

function Numeric ()
  echoKP ("Numeric got clicked!")
end

function Symbolic ()
  echoKP ("Symbolic got clicked!")
end

function Field ()
  echoKP ("Field got clicked!")
end

function Interactive ()
  echoKP ("Interactive got clicked!")
end

callbacks = {"Numeric", "Symbolic", "Interactive", "Field"}


requireKPbuild (5072)



if firstcall then
  firstcall = false
  UI.topMenuInit ({"Numeric", "Symbolic", "Interactive", "Field"},
                  {Numeric,    Symbolic,   Interactive,   Field})
  executeKP (callbacks [RollDie (#callbacks)], [[
    txt clickon "     ARG1     " topMenu    % fix this
  ]]
  )
  
end


--[[

BEGIN HELP
some helpful text should go here...



some helpful text should go here...



some helpful text should go here...
END HELP

--]]
