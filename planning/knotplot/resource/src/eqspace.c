#include <stdio.h>
#include <math.h>

/*
   Program: eqspace.c 

            8 Feb 1996
	    Rob Scharein
	    http://www.cs.ubc.ca/spider/scharein

   takes a file with x, y, z triples and filters
   the points so that they are spaced by a minimum
   amount.

   also takes care that the first and last points are
   different (KnotPlot doesn't like it if they are).

   the resulting file may be read into KnotPlot
   using the 'load' command.

   Note that if you read a file written with the KnotPlot
   command 'coord', you'll have to remove the line that
   reads 'Component 1 of 1:'

   compile with cc -o eqspace eqspace.c -lm

*/

#define TRUE  1
#define FALSE 0

main (c, v)
     int c;
     char **v;
{
  float xstart, ystart, zstart;
  float x, y, z;
  float xlast = 1.0e9, ylast = 1.0e9, zlast = 1.0e9;
  float spacing = .2, spacing_sq;
  int first = TRUE;

  FILE *fp;

  if (c < 2) {
    fprintf (stderr, "\nUsage: %s  list-of-coords [spacing] > new-list-of-coords\n\n", v [0]);
    exit (102);
  }

  if (c > 2) 
    spacing = atof (v [2]);
  
  spacing_sq = spacing * spacing;


  fp = fopen (v [1], "r");

  fprintf (stderr, "Filtering to a spacing of %f.\n", spacing);

  while (fscanf (fp, "%f%f%f", &x, &y, &z) != -1) {
    if (first) {
      xstart = x; ystart = y; zstart = z;
      first = FALSE;
      printf ("%f %f %f\n", x, y, z);
      xlast = x; ylast = y; zlast = z;
    }
    else {
      if (not_too_close (x, y, z, xstart, ystart, zstart, spacing_sq) &&
	  not_too_close (x, y, z, xlast,  ylast,  zlast,  spacing_sq)) {
	printf ("%f %f %f\n", x, y, z);
	xlast = x; ylast = y; zlast = z;
      }
    }
  }

}


not_too_close (x, y, z, xx, yy, zz, min)
     float x, y, z, xx, yy, zz, min;
{
  float dist_sq;

  dist_sq = (x - xx) * (x - xx);
  if (dist_sq > min) return TRUE; 

  dist_sq += (y - yy) * (y - yy);
  if (dist_sq > min) return TRUE;

  dist_sq += (z - zz) * (z - zz);
  if (dist_sq > min) return TRUE;
  
  return FALSE;
}



  
	     
