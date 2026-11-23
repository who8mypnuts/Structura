
/*
  Simple reader for KnotPlot type 1.0 files. 
  Run without the `-snoop' option, prints out
  coordinates, leaving a blank line between components in
  multi-component links. 

  Only handles LOCC, LOCF, LOCD, and LOCS formats.
  Ignores (skips) most data chunks.
  Works for either proper knots or multi-component links. 

  This program does minimal error checking, since it assumes
  that the knot file is valid.

  Rob Scharein, 25 June 2004.

*/

#include <stdio.h>
#include <ctype.h>
#include <stdlib.h>
#include <string.h>

#include "kpf_io.h"

#define is_section(x,y) (!strncmp(x,y,4))

#define TRUE  1
#define FALSE 0

void error_exit (char *s) {
  fprintf (stderr, "\n *** %s\n\n", s);
  exit (0);
}

int component = -1;  // index of component we are currently reading
int vertex_num;      // current vertex number (within a given component)

int snoop = FALSE;

void handle_unknown_section (FILE *fp, char *chunk_ID) {
  int num_to_skip;
  int data_value;

  if (isupper (chunk_ID [0])) {
    if (isupper (chunk_ID [1])) {
      read_int (&num_to_skip, fp);

      if (snoop)
	printf ("Skipping %d bytes in %s array section.\n", num_to_skip, chunk_ID);

      while (num_to_skip--)
	fgetc (fp);
    }
    else {
      read_int (&data_value, fp);

      if (snoop) 
	printf ("Skipping %s data section with data value %d.\n", chunk_ID, data_value);
    }
  }
  else {
    if (snoop)
      printf ("Skipping %s signal section.\n", chunk_ID);
  }
}

void handle_Attr_section (FILE *fp) {
  int attributes;
  read_int (&attributes, fp);

  if (component < 0) 
    error_exit ("Attr chunk seen before comp chunk.\n");

  if (snoop) {
    if (attributes & 1)
      printf ("Component #%d is closed\n", component);
    else
      printf ("Component #%d is open\n", component);
  }
}

void handle_LOCF_section (FILE *fp) {
  int S, N, i;
  float x, y, z;

  if (component < 0) 
    error_exit ("Vertex data seen before comp chunk\n");

  if (snoop) 
    printf ("Adding vertices to Component #%d\n", component);
  
  read_int (&S, fp);
  N = S / 12;    // Number of vertices in this section

  for (i = 0; i < N; i++) {
    if (snoop) 
      printf ("%d: ", vertex_num++);
    read_float (&x, fp);
    read_float (&y, fp);
    read_float (&z, fp);
    printf ("%f %f %f\n", x, y, z);
  }
}


int handle_LOCC_section (FILE *fp) {
  int S, N;
  fvector loc, epsilon;
  float xprev, yprev, zprev;
  float x, y, z;
  signed char xincr, yincr, zincr;

  if (component < 0) 
    error_exit ("Vertex data seen before comp chunk\n");

  if (snoop) 
    printf ("Adding vertices to Component #%d\n", component);

  read_int (&S, fp);
  N = (S - 21) / 3;   // Number of vertices in this section

  read_fvector (epsilon, fp);  // vector offset
  read_fvector (loc, fp);      // starting coordinate

  for (int i = 0; i < N; i++) {

    if (snoop) 
      printf ("%d: ", vertex_num++);

    if (i == 0) {
      x = loc [0];
      y = loc [1];
      z = loc [2];
    }
    else {
      fread (&xincr, 1, 1, fp);
      fread (&yincr, 1, 1, fp);
      fread (&zincr, 1, 1, fp);

      x = xprev + (float) xincr * epsilon [0];
      y = yprev + (float) yincr * epsilon [1];
      z = zprev + (float) zincr * epsilon [2];
    }

    printf ("%f %f %f\n", x, y, z);
    xprev = x;
    yprev = y;
    zprev = z;
  }
}

void handle_LOCD_section (FILE *fp) {
  int S, N, i;
  double x, y, z;

  if (component < 0) 
    error_exit ("Vertex data seen before comp chunk\n");

  if (snoop) 
    printf ("Adding vertices to Component #%d\n", component);

  read_int (&S, fp);

  N = S / 24;    // Number of vertices in this section

  for (i = 0; i < N; i++) {
    if (snoop) 
      printf ("%d: ", vertex_num++);
    read_double (&x, fp);
    read_double (&y, fp);
    read_double (&z, fp);
    printf ("%.14f %.14f %.14f\n", x, y, z);
  }
}

void handle_LOCS_section (FILE *fp) {
  int i, S, N;
  unsigned short usx, usy, usz;
  fvector offset;
  float scale_factor;
  double x, y, z;

  // LOCS files take up about half the space of LOCF files
  // without visible differences (in most cases). 

  if (component < 0) 
    error_exit ("Vertex data seen before comp chunk\n");

  if (snoop) 
    printf ("Adding vertices to Component #%d\n", component);

  read_int (&S, fp);
  N = (S - 16) / 6;    // Number of vertices in this section

  read_float (&scale_factor, fp);
  read_fvector (offset, fp);

  for (i = 0; i < N; i++) {
    read_unsigned_short (&usx, fp);
    read_unsigned_short (&usy, fp);
    read_unsigned_short (&usz, fp);

    x = scale_factor * ((double) usx) + offset [0];
    y = scale_factor * ((double) usy) + offset [1];
    z = scale_factor * ((double) usz) + offset [2];

    if (snoop) 
      printf ("%d: ", vertex_num++);
    printf ("%f %f %f\n", x, y, z);
  }
}


char *read_string (int N, FILE *fp) {
  char *c = (char *) calloc (N + 3, sizeof (char));
  fread (c, N, 1, fp);
  return c;
}

void handle_NAME_section (FILE *fp) {
  int N;
  
  read_int (&N, fp);
  char *knot_name = read_string (N, fp);
  printf ("NAME \"%s\"\n", knot_name);
  free (knot_name);
}


void handle_META_section (FILE *fp) {
  int N;
  read_int (&N, fp);
  int sizeName, sizeValue;
  read_int (&sizeName, fp);
  sizeValue = N - sizeName - 4;
  char *name = read_string (sizeName, fp);
  char *value = read_string (sizeValue, fp);
  printf ("META \"%s\" \"%s\"\n", name, value);
  free (name);
  free (value);
}

void handle_COLR_section (FILE *fp) {
  float r, g, b;
  int S;
  read_int (&S, fp);
  read_float (&r, fp);
  read_float (&g, fp);
  read_float (&b, fp);
  printf ("COLR %f %f %f\n", r, g, b);
}

int main (int argc, char **argv) {
  char chunk_ID [5];
  FILE *fp;
  
  if (argc < 2) {
    fprintf (stderr, "Usage:   %s  [options] KPfile\n", argv [0]);
    fprintf (stderr, "         where options are:\n");
    fprintf (stderr, "         -snoop   (turns on verbose output)\n");
    fprintf (stderr, "Examples:\n");
    fprintf (stderr, "           %s myknot.k\n", argv [0]);
    fprintf (stderr, "           %s -snoop myknot.k\n", argv [0]);
    exit (1);
  }

  int index;

  for (index = 1; index < argc - 1; index++) {
    if (!strcmp ("-snoop", argv [index]))
	snoop = TRUE;
  }

  fp = fopen (argv [index], "r");
  
  if (!fp) {
    fprintf (stderr, "Can't open file `%s'.\n", argv [1]);
    exit (1);
  }

  /* Determine what kind of file it is. */

  char comment [20];
  fread (comment, 12, 1, fp);

  if (strncmp (comment, "KnotPlot 1.0", 12)) {
    fclose (fp);
    fprintf (stderr, "File `%s' is not a KnotPlot file.\n", 
	     argv [1]);
    exit (1);
  }

  /* If we get this far, then we have a KnotPlot 1.0 format file. */
  /* Scan to control L and then read one character. */

  while (fgetc (fp) != 12);  // Empty loop to scan to control-L.
  fgetc (fp);                // This character is arbitrary, so ignore.

  do {
    if (fread (chunk_ID, 1, 4, fp) != 4) {
      fprintf (stderr, " *** End of data before end of file `%s'.\n",
	       argv [1]);
      exit (1022);
    }
    chunk_ID [4] = '\0';

    if (snoop)
      printf ("\n%s chunk\n", chunk_ID);

    if (is_section (chunk_ID, "endf")) {  // end of file chunk
      fclose (fp); 
      exit (0);
    }
    else if (is_section (chunk_ID, "LOCF"))
      handle_LOCF_section (fp);
    else if (is_section (chunk_ID, "LOCD"))
      handle_LOCD_section (fp);
    else if (is_section (chunk_ID, "LOCS"))
      handle_LOCS_section (fp);
    else if (is_section (chunk_ID, "LOCC"))
      handle_LOCC_section (fp);
    else if (is_section (chunk_ID, "Attr"))
      handle_Attr_section (fp);
    else if (is_section (chunk_ID, "COLR"))
      handle_COLR_section (fp);
    else if (is_section (chunk_ID, "NAME"))
      handle_NAME_section (fp);
    else if (is_section (chunk_ID, "META"))
      handle_META_section (fp);
    else if (is_section (chunk_ID, "comp")) {
      ++component;
      if (snoop)
	printf ("Starting component #%d:\n", component);
      else
	if (component > 0) printf ("\n");
      vertex_num = 0;
    }
    else 
      handle_unknown_section (fp, chunk_ID);
    
  } while (TRUE);
}
