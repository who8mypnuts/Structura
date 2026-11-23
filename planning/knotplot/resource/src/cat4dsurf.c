/* cat4dsurf.c 
   
   This program concatenates two KnotPlot 4D surfaces
   into one.

   */

#include <stdio.h>
#include <math.h>

typedef float real;
typedef int   boolean;
typedef float vector [3];

typedef struct {
  vector v;
  real w;
} vector4;


typedef struct {
  vector4 vertex4 [4];
  vector vertex [4];
  vector normal [2];
  unsigned long colour;
  unsigned char active;
} SpinSegment4d;



main (argc, argv)
     int argc;
     char **argv;
{
  long i, N, M, Total;
  FILE *fp1, *fp2;
  SpinSegment4d gumby;

  if (argc < 3) {
    fprintf (stderr, "USAGE: %s surf1 surf2  > newsurf\n",
	     argv [0]);
    exit (102);
  }

  fp1 = fopen (argv [1], "r");
  if (!fp1) {
    fprintf (stderr, "Can't open file `%s'.\n",
	     argv [1]);
    exit (1022);
  }

  fp2 = fopen (argv [2], "r");
  if (!fp2) {
    fprintf (stderr, "Can't open file `%s'.\n",
	     argv [2]);
    exit (1022);
  }
    
  fread (&N, 1, sizeof (long), fp1);
  fread (&M, 1, sizeof (long), fp2);
  Total = N + M;

  fwrite (&Total, 1, sizeof (long), stdout);
  
  for (i = 0; i < N; i++) {
    fread  (gumby.vertex4, 4, sizeof (vector4), fp1);
    fwrite (gumby.vertex4, 4, sizeof (vector4), stdout);
  }

  for (i = 0; i < M; i++) {
    fread  (gumby.vertex4, 4, sizeof (vector4), fp2);
    fwrite (gumby.vertex4, 4, sizeof (vector4), stdout);
  }


}





  

