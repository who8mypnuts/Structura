#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

/*

  KnotPlot file snooper, example usage:

  kpfsnoop myknot.k            prints out lots of info about all the sections
                               (fields or chunks) found in the knot file
  kpfsnoop -b myknot.k         just prints one integer, the number of beads
  kpfsnoop -c myknot.k         just prints one integer, the number of components

*/

char comment [200];

#define is_section(x,y) (!strncmp(x,y,4))
#define TRUE  1
#define FALSE 0

void read_int (int *val, FILE *fp) {
  unsigned char a, b, c, d;
  fread (&a, 1, 1, fp);
  fread (&b, 1, 1, fp);
  fread (&c, 1, 1, fp);
  fread (&d, 1, 1, fp);
  *val = (a << 24) | (b << 16) | (c << 8) | d;
}

int main (int argc, char **argv) {
  /* This is the load routine for KnotPlot Link File Version 1.0
     developed on 26 Feb 1996. */

  FILE *fp;
  char sname [5];
  int looping;
  int num_to_skip, data_value;
  int blurt = TRUE, print_nbeads = TRUE, print_ncomps = TRUE;
  int nbeads, total_beads = 0, index = 1, ncomps = 0;

  if (argc < 2) {
    fprintf (stderr, "Usage: %s  [options] KnotPlot-file\n", argv [0]);
    exit (1022);
  }

  if (argc == 3) {
    if (!strcmp (argv [1], "-b")) {
      print_nbeads = TRUE;
      print_ncomps = FALSE;
      blurt = FALSE;
      index++;
    }
    else if (!strcmp (argv [1], "-c")) {
      print_ncomps = TRUE;
      print_nbeads = FALSE;
      blurt = FALSE;
      index++;
    }
  }

  if (blurt) printf ("KnotPlot File Snooper: %s\n", argv [index]);
  
  fp = fopen (argv [index], "r");

  if (!fp) { 
    fprintf (stderr, "Can't open file `%s'.\n", argv [index]);
    exit (1022);
  }
  
  /* Determine what kind of file it is. */

  fread (comment, 12, 1, fp);

  /* Old style link file will start with two zero bytes or 
     with the string View-M. */

  if ((comment [0] == (char) 0 && comment [1] == (char) 0) ||
      !strncmp (comment, "View-M", 6)) {
    fclose (fp);
    if (blurt) printf ("Probably an old style format knot or link file.\n");
    exit (102);
  }

  /* It is a ascii coord file if it doesn't begin with the string
     KnotPlot 1.0. */

  else if (strncmp (comment, "KnotPlot 1.0", 12)) {
    fclose (fp);
    if (blurt) printf ("Possibly an ascii coord file.\n");
    exit (1022);
  }


  /* If we get this far, then we have a KnotPlot 1.0 format file. */
  /* Scan to control L and then read one character. */

  while (fgetc (fp) != 12);  /* Empty loop. */
  fgetc (fp);                /* This character is arbitrary. */

  looping = TRUE;

  do {
    if (fread (sname, 1, 4, fp) != 4) {
      if (blurt) printf (" *** End of data before end of file.\n");
      exit (1022);
    }
    sname [4] = '\0';

    if (is_section (sname, "endf"))
      looping = FALSE;
    if (is_section (sname, "comp"))
      ncomps++;

    if (blurt) printf ("Field %s: ", sname);
    if (isupper (sname [0])) {
      if (isupper (sname [1])) {
	read_int (&num_to_skip, fp);
	if (blurt) printf ("%d bytes of data", num_to_skip);
	
	nbeads = 0;
	if (is_section (sname, "LOCF"))
	  nbeads = num_to_skip / 12;
	else if (is_section (sname, "LOCD"))
	  nbeads = num_to_skip / 24;
	else if (is_section (sname, "LOCI"))
	  nbeads = num_to_skip / 12;
	else if (is_section (sname, "LOCS"))
	  nbeads = (num_to_skip - 16) / 6;
	else if (is_section (sname, "LOCC"))
	  nbeads = (num_to_skip - 21) / 3;
	else if (is_section (sname, "CUBE")) {
	  read_int (&nbeads, fp);
	  num_to_skip -= 4;
	}
	if (blurt) {
	  if (nbeads)
	    printf (", %d beads", nbeads);
	  printf ("\n");
	}
	
	total_beads += nbeads;
	
	while (num_to_skip--)
	  fgetc (fp);
      }
      else {
	read_int (&data_value, fp);
	if (blurt) printf ("Data (int) = %d\n", data_value);
      }
    }
    else {
      if (!islower (sname [0]) || !islower (sname [1])) 
	printf ("Illegal values found in section name (%d, %d).\n", (int) sname [0], (int) sname [1]);
      if (blurt) printf ("marker field\n");
    }

  } while (looping);
  
  if (print_nbeads) {
    if (blurt) printf ("Total number of beads is ");
    printf ("%d\n", total_beads);
  }
  if (print_ncomps) {
    if (blurt) printf ("Total number of components is ");
    printf ("%d\n", ncomps);
  }

  return 0;

}



