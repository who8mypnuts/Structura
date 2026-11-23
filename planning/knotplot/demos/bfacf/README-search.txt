BFACF Fancy Help - Search for Minimal Stick Candidates

This help window only discusses issues specific to the search for minimal
stick candidates.

Click on the `README' button in the `Cavities' section to see an explanation
about general features of this control panel.

`minbox' attempts to find a minimal stick candidate on the cubic lattice,
constraining the knot to be within a small box.  The box, although small, is
large enough to make no difference to finding the minimal stick candidate
than would be the case in an unconstrained geometry.

`minslab' is much more interesting than `minbox'.  Knots are easily observed
to have different minimal stick numbers in the slab case than they do in the 
unconstrained case.   The `minslab' demo is an older demo.  The newer 
`2-slab' demo is probably more interesting to use. 

`1-slab', `2-slab' and `3-slab' attempt to force a knot into a slab of height 1, 2 or 3, 
respectively.  The knot starts out on the right hand side in the tall end of
a wedge which is attached to the slab along the boundary x = 0.  There is a 
movable wall which will eventually for the knot into the wedge.  This wall 
will attempt to move automatically after you click the `start' button. You can 
also move this wall manually by clicking the one of the `move wall' buttons.

Once the wall moves to x = 0, automatic seaching for the minimal step knot
will begin.  You can at any time stop the process and retrieve the best min found.

For all the above simulations, click on the buttons in the `Configurations:'
section until you get a knot you're interested in.  For the `1-slab' and `2-slab'
demos you can also load a specific knot by using a `kload' command.  For
example, 

   kload 10 108

will load the knot 10_108 into the wedge.  

After you have a knot to study, click on the `start'' button to  
start things going.  To increase the search speed vastly, change the `set step' 
slider to `1000000' on the Control Panel.  Try fiddling with the z slider or 
the p(+2), p(0) and p(-2) sliders individually.  Suddenly changing the z value 
to 0 seems to improve the rate at which minimal stick candidates are found. 
 
While searching for the minimum, KnotPlot will inform you of its progress in the candidate.  
Check the output in the Command Window. When you think you can't improve the search 
result any more, click on the `retrieve min' button.  Enjoy viewing your newly found candidate!
If you choose to save it, use one of the following commands:

save MYKNOT int
save MYKNOT news

First version saves the knot in plain text, one vertex per line (three integers).
Second version saves the knot in plain text DUNEWS format (Down, Up, North, ...).
In this format, one of Diao's minimal stick trefoils would be written as
NNNWWSSDEEEUUWWDNDDESSUU



NOTE: Use the button below to close this window:

