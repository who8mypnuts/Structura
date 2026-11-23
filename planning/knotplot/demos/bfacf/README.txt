BFACF Fancy Help - Cavities

Click on one of the buttons in the Cavities section at the top of the 
KnotPlot Control Panel.  This will setup one of several constrained geometries.
In the view window, you should see a cubic lattice knot or link sitting inside
the cavity. The little dots represent the boundaries of the cavity, these are
filled cells into which the edges of the knot are not permitted to wander.

To see the cavity walls better, it's helpful to rotate the view using the
left mouse button.  

Now click on the `run' button and move the `step size' slider to a value of 1. 
This will show you every BFACF step, and will be very slow as most of the time 
is spent updating the display.  A step size of 1000 is pretty good to get good 
performance but still see the knot evolve over time. A step size of 1000000 is 
super fast, but there will be no correlation between display updates.  

To stop the simulation, click the `stop' button.

While the simulation is running, you can change the value of z using the 
slider at the bottom.  Notice how the probabilities change along with it.
Alternatively, you can adjust the individual probabilities separately.
Increasing the z-value to 1 will cause the knot to fill the space.  

For convenience, there are also two buttons in the view window:

    run normally --- equivalent to setting z to 0.20815 and running with step
                     size 1000.  Same as KnotPlot command
                     bfacf run 1000

    fill cavity  --- equivalent to setting z to 1 and running with step 
                     size 1000000.  Equivalent to 
                     bfacf run 1000000

WHATEVER YOU DO, DON'T ENABLE AUTO-CENTERING WHILST RUNNING INSIDE A CAVITY!!

NOTE: Use the button below to close this window:

