#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "kpf_io.h"

/* 

   minimal program to write a knot in KnotPlot 1.0 format

   can only write single component (proper) knots

   doesn't support open components

   only writes double precision (LOCD) vertex chunks

   when loaded into KnotPlot should see a figure-8 knot

*/

#define NVERT 22

dvector vertex [NVERT] = {
  {-6.433372, -2.581908, -0.898330},
  {-5.216500, -5.448181, 0.904838},
  {-2.195621, -6.828723, 2.180323},
  {1.069656, -5.699327, 1.550406},
  {1.485231, -3.066516, -0.936731},
  {-1.020783, -0.514474, -1.353337},
  {-2.693583, 1.894929, 1.020740},
  {-2.379443, 5.389005, 1.759114},
  {0.056070, 7.410400, 0.137613},
  {2.633190, 5.984021, -1.824147},
  {3.207317, 2.489743, -1.761993},
  {1.754950, -0.090048, 0.553077},
  {-0.762637, -2.630406, 1.014367},
  {-0.834543, -5.183004, -1.616036},
  {2.334852, -6.197227, -2.851875},
  {5.414476, -4.761066, -1.698645},
  {6.502538, -1.990574, 0.362254},
  {5.532320, 1.076698, 2.003704},
  {2.718865, 3.281561, 1.845071},
  {-0.129765, 3.727484, -0.604402},
  {-3.149582, 3.095948, -2.626344},
  {-5.728402, 0.621285, -2.398516}};


int main (int argc, char **argv) {
  if (argc < 2) {
    fprintf (stderr, "Usage: kpfwrite MYKNOTFILE\n");
    exit (102);
  }
  bool success = minimal_write_buffer_to_KnotPlot_file (vertex,      // vertex array
							NVERT,       // number of vertices in vertex array
							argv [1]);   // file to contain knot coordinate data
  if (success) 
    printf ("success\n");
  else
    printf ("failure\n");
  return 0;
}
