reset all
back=0
scale = 0.663772

grmode=1
grmaj=67
grmin=2
3dop colG 0 1 1
3dop colg 102.2 1 1

spe grid

knot 
cyl=.1
hstar=222
hincr=0

if \rr2 < 1 then "rot x -45;scale=0.868;try=3.126"

idle "rot z -.1;about z .2"
