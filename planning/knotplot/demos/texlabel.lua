--[[

rob scharein, 24 july 2023

render a label in TeX and Ghostscript

--]]

local defs = [[
\nopagenumbers
\parindent=0pt
\parskip=0pt
\lineskip=0pt

\pdfpagewidth=.75in   % was .5in
\pdfpageheight=.2in


\hoffset=-1in
\voffset=-1in
\hsize=.75in
\vsize=.2in
\hbox to \hsize{\hss
]]

local enddefs = [[
  \hss}
  
  \end

]]


function texlabel1 (tex, x, y, z, s)
  local fp = io.open ("_t.tex", "w")
  io.output (fp)
  io.write (defs .. tex .. enddefs)
  io.close (fp)
  os.execute ("pdftex _t.tex")
  os.execute ("gs -dSAFER -dBATCH -dNOPAUSE -sDEVICE=pnggray -r3000 -sOutputFile=_t.png _t.pdf")
  os.execute ("mogrify -resize x100 _t.png")
  os.execute ("frame.php _t.png")
  os.execute ("cp _t.pam t.pam")
  os.execute ("cp _t.png t.png")
  executeKP (x, y, z, s, [[
    scenery vscale ARG4
    scenery object _t-n ARG1 ARG2 ARG3
  ]])
  os.execute ("/bin/rm _t*")
end

-- convert input.png -fuzz 10% -transparent white output.png

function texlabel (tex, x, y, z, s)
  local fp = io.open ("_t.tex", "w")
  io.output (fp)
  io.write (defs .. tex .. enddefs)
  io.close (fp)
  os.execute ("pdftex _t.tex")
  os.execute ("gs -dSAFER -dBATCH -dNOPAUSE -sDEVICE=pnggray -r3000 -sOutputFile=_t1.png _t.pdf")
  os.execute ("convert _t1.png -resize x100 -fuzz 10% -transparent white -trim _t.png")
  os.execute ("frame.php _t.png")
  --os.execute ("cp _t.pam t.pam")
  --os.execute ("cp _t.png t.png")
  executeKP (x, y, z, s, [[
    scenery vscale ARG4
    scenery object _t-n ARG1 ARG2 ARG3
  ]])
  os.execute ("cp _t.png i.png")
  os.execute ("/bin/rm _t*")
end


