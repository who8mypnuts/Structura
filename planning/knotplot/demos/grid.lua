--[[

rob scharein
Thursday, 11-Apr-24 02:31:18 UTC

--]]

if requireKPbuild (5058) then
  executeKP (paramKP ("vscale"),         -- gets the current value of vscale
             captureKP ("rotate euler"), -- gets the current rotation as euler angles
             paramKP ("grsize"),
    [[
      show -push
      show +grid
      grsize = 10
      vscale = 0.45
      untran
      tfunction 3 "vscale = ARG1;rotate ARG2;grsize = ARG3;show -pop"
    ]])
else
  echoKP ("needs KPbuild of at least 5058")
end
