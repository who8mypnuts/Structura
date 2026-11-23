#include <stdio.h>

unsigned char red [4], green [4], blue [4];

#define TRUE  1
#define FALSE 0

main (argc, argv)
     int argc;
     char **argv;
{
  int s;
  FILE *fp;
  long xsize, ysize;
  long value, numpixels;
  long rows, cols, depth, sign, index = 0;
  char sc;
  unsigned char r, g, b;
  unsigned char uc;
  int i, j, n;  
  int xorigin = 0, yorigin = 0;
  int *cursor;
  int row, col;

  switch (argc) {
  case 3:
    xorigin = yorigin = atoi (argv [2]);
    break;
  case 4:
    xorigin = atoi (argv [2]);
    yorigin = atoi (argv [3]);
    break;
  case 1:
    fprintf (stderr, 
	     "USAGE:  %s rawPPMfile [xorig [yorig]] > KnotPlotCursorFile\n",
	     argv [0]);
    exit (-1);
  }
    
  if (!open_ppm (&fp, argv [1], &xsize, &ysize)) exit (-1);
  
  rows = ysize;
  cols = xsize;

  if (rows > 32 || cols > 32) 
    fprintf (stderr, "Must be no larger than 32 by 32 PPM image.\n");

  numpixels = rows * cols;

  cursor = (int *) calloc (32 * 32, sizeof (int));

  for (row = 0; row < rows; row++) {
    for (col = 0; col < cols; col++) {
      fread (&r, 1, sizeof (unsigned char), fp);
      fread (&g, 1, sizeof (unsigned char), fp);
      fread (&b, 1, sizeof (unsigned char), fp);
      cursor [(31 - row) * 32 + col] = colour (r, g, b);
    }
  }    
  fclose (fp);

  for (i = 1; i < 4; i++) 
    printf ("%d %d %d ", red [i], green [i], blue [i]);
  printf ("\n");
  printf ("%d %d\n", xorigin, yorigin);
  


  for (i = 0, index = 0; i < 64; i++) {
    value = 0;
    for (j = 0; j < 16; j++, index++) {
      if (cursor [index] & 0x01) s = 1;
      else s = 0;
      value |= (s << (15 - j));
    }
    printf ("%d ", value);
  }
  printf ("\n");
  
  for (i = 0, index = 0; i < 64; i++) {
    value = 0;
    for (j = 0; j < 16; j++, index++) {
      if (cursor [index] & 0x02) s = 1;
      else s = 0;
      value |= (s << (15 - j));
    }
    printf ("%d ", value);
  }
  printf ("\n");
}





int numfound = 0;

int colour (r, g, b)
     unsigned char r, g, b;
{
  int i;

  for (i = 0; i < numfound; i++) {
    if (r == red [i] &&
	g == green [i] &&
	b == blue [i]) 
      return i;
  }

  if (numfound < 4) {
    red [numfound] = r;
    green [numfound] = g;
    blue [numfound] = b;
    numfound++;
    return numfound - 1;
  }

  return 0;
}



open_ppm (pfp, file_name, pxs, pys)
     FILE **pfp;
     char *file_name;
     long *pxs, *pys;
{
  char in_line [300];
  FILE *fp;

  fp = fopen (file_name, "r");
  if (fp == (FILE *) NULL) {
    fprintf (stderr, "Can't open file `%s'.\n", file_name);
    return FALSE;
  }
  *pfp = fp;
  
  fgets (in_line, 30, fp);

  if (in_line [0] != 'P' || in_line [1] != '6') {
    fprintf (stderr, "File `%s' not a raw PPM file.\n", file_name);
    return FALSE;
  }
  get_a_line (in_line, 300, fp);
  sscanf (in_line, "%d%d", pxs, pys);

  get_a_line (in_line, 300, fp);

  return TRUE;
}

get_a_line (in_line, s, fp)
     char *in_line;
     int s;
     FILE *fp;
{
  int looping = TRUE;
  do {
    fgets (in_line, 300, fp);
    if (!(in_line [0] == '\n' || in_line [0] == '#'))
      looping = FALSE;
  } while (looping);
}

