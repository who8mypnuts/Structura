--[[

  exploring the simple interface to the MIDI synthesizer
  
  rob scharein, 17 february 2023
  
--]]

if demo ~= luaSource then
  demo = luaSource
  executeKP ([[
    reset all
    play init
    txt on
    txt clobber on
    txt font 4
    txt fill on
    txt centre
    %txt c 50 "play close" "play close;play init"
    txt font 3
    alias ~play "lua . Play($0)"
  ]])

  Demo ()
  Title ("something about MIDI demo")
  
  spacing = 33
  executeKP ("txt phantom 102")
  sustainTime = 3
  noteName = explode (",", "C,C#/Db,D,D#/Eb,E,F,F#/Gb,G,G#/Ab,A,A#/Bb,B")
  
 
  
  function Play (note)
    executeKP (note, sustainTime, [[
      play ARG1
      echo play ARG1
      tfunc ARG2 "play ARG1 0;echo play ARG1 0"
    ]])
  end
  
  yPos = -40
  spacing = 36
  executeKP (yPos, string.format ("%.1f", sustainTime), [[
    txt centre
    txt fill off
    txt push
    txt font 4
    txt left
    txt c-267 ARG1 "play a note:"
    txt centre
    txt pop
    txt phantom C#Db"
  ]])
  
  yPos = yPos - spacing * 0.8
  note = 1
  for octave = -3, 8 do
    for i = 1, 12 do
      col = (i - 1) % 12
      xPos = (col - 5.5) * spacing * 1.4
      if octave == -3 then
        executeKP (i, xPos, yPos, noteName [i], [[
          txt cARG2 ARG3 "ARG4"
        ]])
      else
        if note < 129 then
          executeKP (note, xPos, yPos, [[
            txt fill on
            txt phantom 102
            txt cARG2 ARG3 'ARG1' "~play ARG1"
          ]])
          note = note + 1
        end
      end
    end
    if octave == -3 then
      sideText = "octave"
    else
      sideText = octave
    end
    executeKP (xPos + 50, yPos, sideText, [[
      txt fill off
      % x-position is relative to centre of window
      % y-position is relative to top of window
      txt cARG1 ARG2 'ARG3'
    ]])
    yPos = yPos - spacing * 0.8
  end
  
  yPosInst = yPos
  
  executeKP (yPos, [[
    txt push
    txt left
    txt font 4
    txt c-267 ARG1 "choose an instrument:"
    txt pop
    txt fill on
  ]])
  
  for i = 1, 128 do
    row = math.floor ((i - 1) / 16)
    col = (i - 1) % 16
    if col == 0 then
      yPos = yPos - spacing * 0.8
    end
    xPos = (col - 7.5) * spacing * 1.2
    executeKP (i, xPos, yPos, [[
      txt cARG2 ARG3 'ARG1' "play p ARG1;echo play p ARG1;lua . Update ()"
    ]])
  end

  
  executeKP ([[
    txt phantom
    txt c 20 "Wikipedia page on General MIDI standard" "play wiki"
    play p 1
  ]])
end



function Update ()
  local stuff = lcaptureKP ("play p")
  local text = ""
  local space = ""
  
  for i = 2, #stuff do
    text = text .. space .. stuff [i]
    space = " "
  end
  executeKP (yPosInst, stuff [1], text, [[
    txt push
    txt fill off
    txt centre
    txt font 4
    txt c ARG1 "ARG3"
    txt right
    txt c+340 ARG1 "play p ARG2"
    txt pop
  ]])
end

st_yPos = yPos - spacing

changeRatio = math.sqrt (math.sqrt (2))
--print ("ratio is " .. changeRatio)

function ChangeSustainTime (way)
  if way == "+" then
    if sustainTime < 10.2 then
      sustainTime = changeRatio * sustainTime
    end
  else
    if sustainTime > 0.04 then
      sustainTime = sustainTime / changeRatio
    end
  end
  
  executeKP (st_yPos, string.format ("%.1f", sustainTime), [[
    txt push
    txt font 4
    txt left
    txt fill off
    txt c-340 ARG1 "ARG2 second sustain time"
    txt fill on
    txt c-130 ARG1 "-" "lua . ChangeSustainTime ('-');display true"
    txt c-95 ARG1 "+" "lua . ChangeSustainTime ('+');display true"
    txt pop
  ]])
end

sustainTime = sustainTime / changeRatio
ChangeSustainTime ("+")
Update ()

yPos = yPos - 2 * spacing

executeKP ([[
  txt push
  txt centre
  txt font 4
  txt fill off
  txt group 9827
  txt expire 25
  txt c 76 "before you click on any of the buttons above,"
  txt c 55 "be sure your volume is not too loud"
  txt pop
]])


--[[

  demo should use either 0 or 1 relative
  show note names
  one row per octave
  like in https://computermusicresource.com/midikeys.html
  

--]]
