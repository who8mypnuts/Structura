#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define TWOPI        6.28318530717958647693

/* 
   Rob Scharein
   9 March 1996

   This is a very simple example program that creates 
   a stack of unknots in the KnotPlot 1.0 file format.

*/


void write_int (int *val, FILE *fp) {
  // write a big-endian int to a file
  unsigned char a, b, c, d;
  
  a = (unsigned char) (0xff & (*val) >> 24);
  b = (unsigned char) (0xff & (*val) >> 16);
  c = (unsigned char) (0xff & (*val) >> 8);
  d = (unsigned char) (0xff & (*val));

  fwrite (&a, 1, 1, fp);
  fwrite (&b, 1, 1, fp);
  fwrite (&c, 1, 1, fp);
  fwrite (&d, 1, 1, fp);
}

void write_float (float *val, FILE *fp) {
  union {
    float f;
    int i;
  } x;

  x.f = *val;
  write_int (&x.i, fp);
}

int main (int argc, char **argv) {
  float x, y, z;
  int N, B = 20;
  float r = 8.2;
  float theta, theta_inc;
  int comp, bead;
  int num_bytes;

  switch (argc) {
  case 4:
    r = atof (argv [3]);
  case 3:
    B = atoi (argv [2]);
  case 2:
    N = atoi (argv [1]);
    break;
  default:
    fprintf (stderr, "Usage: %s N [B [r]] > myfile\n", argv [0]);
    fprintf (stderr, "       Creates a stack of N unknots with B beads each and radius r.\n");
    exit (102);
  }


  fprintf (stderr, 
	   "Creating a stack of %d unknots: %d beads each, radius %f\n",
	   N, B, r);
  theta_inc = TWOPI / (float) B;

  /* First write the header. */

  printf ("KnotPlot 1.0  %c\n", (char) 12);  /* Control-L */

  /* Set the z coordinate of component 0, 
     components will be spaced a distance of 3 apart. */

  z = (float) (N - 1) * 1.5;

  /* Loop thru the number of components. */

  for (comp = 0; comp < N; comp++, z -= 3.0) {

    /* For each component, emit a `comp' field 
       to indicate start of component. */

    printf ("comp");    

    /* The data will be written using a `LOCF' (location float) field
       of size 12B (4 is sizeof (float) and B is number of beads 
       and each bead has 3 coords).

       Note that this 12B bytes does not include the four byte field
       name LOCF and the four bytes used to store the value of num_bytes.

       Total size of the field is therefore 12B + 8 bytes. */

    num_bytes = 12 * B;

    printf ("LOCF");
    write_int (&num_bytes, stdout);
   
    /* Now loop thru number of beads for this component. */

    for (theta = 0.0, bead = 0; bead < B; bead++, theta += theta_inc) {
      x = r * cos (theta);
      y = r * sin (theta);
      
      write_float (&x, stdout);
      write_float (&y, stdout);
      write_float (&z, stdout);
    }
  }

  /* Finally, write a `endf' field to indicate end of file. */

  printf ("endf");

}
