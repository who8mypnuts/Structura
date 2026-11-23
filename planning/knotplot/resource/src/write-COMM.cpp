
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/*
  Programme to write a KnotPlot file 
  with a single COMM (command) chunk.
*/

void write_int (int *val, FILE *fp) {
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

#define BUFFER_SIZE 102000

int main (int c, char **v) {
  int S, len = 0;
  char cnull = (char) 0;
  char chunk [5] = "COMM";
  bool read_from_file = false;
  char *buffer = (char *) calloc (BUFFER_SIZE, sizeof (char));

  if (c < 2) {
    fprintf (stderr, "Usage:  %s [options] command > KnotPlotFile\n", v [0]);
    fprintf (stderr, "        options are:\n");
    fprintf (stderr, "            -t        write a TEXT chunk\n");
    fprintf (stderr, "            -n        write a NOTE chunk\n");
    fprintf (stderr, "            -s        write a SPEC chunk\n");
    fprintf (stderr, "            -f FILE   read contents of FILE\n");
    exit (102);
  }

  int index = 1;
  while (index < c && v [index][0] == '-') {
    if (!strcmp (v [index], "-t")) {
      strcpy (chunk, "TEXT");
    }
    else if (!strcmp (v [index], "-n")) {
      strcpy (chunk, "NOTE");
    }
    else if (!strcmp (v [index], "-s")) {
      strcpy (chunk, "SPEC");
    }
    else if (!strcmp (v [index], "-f")) {
      read_from_file = true;
      char ch;
      index++;
      FILE *fp = fopen (v [index], "r");
      if (!fp) {
	fprintf (stderr, " *** can't open file `%s'\n", v [index]);
	exit (34);
      }
      while ((ch = fgetc (fp)) != EOF) {
	buffer [len++] = ch;
      }
      fclose (fp);
    }
    index++;
  }


  if (!read_from_file) 
    len = strlen (v [index]);

  S = ((len + 3) / 4) * 4;

  fprintf (stdout, "KnotPlot 1.0  %c\n", (char) 12);  /* Control-L */

  printf ("%s", chunk);
  write_int (&S, stdout);

  if (read_from_file)
    fwrite (buffer, len, 1, stdout);
  else
    printf ("%s", v [index]);

  S -= len;

  while (S--)
    fwrite (&cnull, 1, 1, stdout);

  fprintf (stdout, "endf\n\n\n\n");

  return 1;
}



  
