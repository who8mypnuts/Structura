#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/*
  Programme to write a KnotPlot file 
  with a single NAME (the knot name) chunk.
*/

void write_long (long *val, FILE *fp) {
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

int main (int c, char **v) {
  long S, len;
  char cnull = (char) 0;

  if (c < 2) {
    fprintf (stderr, "Usage:  %s command > KnotPlotFile\n", v [0]);
    exit (102);
  }

  len = strlen (v [1]);

  S = ((len + 3) / 4) * 4;

  fprintf (stdout, "KnotPlot 1.0  %c\n", (char) 12);  /* Control-L */

  printf ("NAME");
  write_long (&S, stdout);

  printf ("%s", v [1]);

  S -= len;

  while (S--)
    fwrite (&cnull, 1, 1, stdout);

  fprintf (stdout, "endf\n\n\n\n");

  return 1;
}



  
