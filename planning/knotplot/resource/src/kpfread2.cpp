
/*
  Simple reader for KnotPlot type 1.0 files. 

  Only handles LOCC, LOCF, LOCD, and LOCS formats.
  Ignores (skips) most data chunks.
  
  Only works for single component knots. 

  Only supports one vertex chunk.

  This program does minimal error checking, since it assumes
  that the knot file is valid.

  Rob Scharein, January 2011

*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "kpf_io.h"

#define TRUE  1
#define FALSE 0


int main (int argc, char **argv) {
  
  if (argc < 2) {
    fprintf (stderr, "Usage:   %s KPfile\n", argv [0]);
    exit (1);
  }

  int max_num_vert = 30000;
  dvector *vertex = (dvector *) calloc (max_num_vert, sizeof (dvector));
  
  int N_vertices = minimal_read_KnotPlot_file_into_buffer (argv [1], vertex, max_num_vert);
  if (N_vertices == 0) {
    fprintf (stderr, " *** something went wrong!\n");
    exit (102);
  }
  
  // print out what was found

  printf ("%d vertices read\n", N_vertices);

  for (int i = 0; i < N_vertices; i++) 
    printf ("%f %f %f\n", 
	    vertex [i][0],
	    vertex [i][1],
	    vertex [i][2]);

}
