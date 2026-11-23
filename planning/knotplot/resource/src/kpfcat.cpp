#include <stdio.h>
#include <ctype.h>
#include <string.h>
#include <stdlib.h>

/* 
    Programme to concatenate a bunch of KnotPlot files. 

    Rob Scharein
    25 June 2004

    Why would you want to do this?  Well, suppose
    you had a knot file and you wanted to add a name 
    to it.  You could do something like the following:
    write-NAME "this is my knot" > a
    kpfcat a myknot.k > tmp
    mv tmp myknot.k
    /bin/rm a tmp

    Rob Scharein
    14 April 2011 

*/

char comment [200];

#define is_section(x,y) (!strncmp(x,y,4))
#define TRUE  1
#define FALSE 0

void copy_file (char *);

void read_long (long *val, FILE *fp) {
  unsigned char a, b, c, d;
  fread (&a, 1, 1, fp);
  fread (&b, 1, 1, fp);
  fread (&c, 1, 1, fp);
  fread (&d, 1, 1, fp);
  *val = (a << 24) | (b << 16) | (c << 8) | d;
}

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


int main (int argc, char **argv) {
  int c = 1;

  if (argc < 2) {
    fprintf (stderr, "Usage: %s  file1 file2 ... fileN > newfile\n", argv [0]);
    exit (1022);
  }

  fprintf (stdout, "KnotPlot 1.0  %c\n", (char) 12);  /* Control-L */
  while (c < argc) copy_file (argv [c++]);
  fprintf (stdout, "endf\n\n\n\n");
}

void copy_file (char *file_name) {
  char sname [5];
  long num_to_skip, data_value;
  FILE *fp;
  
  fp = fopen (file_name, "r");
  
  /* Determine what kind of file it is. */

  fread (comment, 12, 1, fp);
  fprintf (stderr, "copying %s\n", file_name);

  if (strncmp (comment, "KnotPlot 1.0", 12)) {
    fclose (fp);
    fprintf (stderr, "File `%s' is not a KnotPlot file.\n", 
	     file_name);
    return;
  }

  /* If we get this far, then we have a KnotPlot 1.0 format file. */
  /* Scan to control L and then read one character. */

  while (fgetc (fp) != 12);  /* Empty loop. */
  fgetc (fp);                /* This character is arbitrary. */

  do {
    if (fread (sname, 1, 4, fp) != 4) {
      fprintf (stderr, " *** End of data before end of file `%s'.\n",
	       file_name);
      exit (1022);
    }
    sname [4] = '\0';

    if (is_section (sname, "endf")) {
      fclose (fp); return;
    }

    printf ("%s", sname);
    if (isupper (sname [0])) {
      if (isupper (sname [1])) {
	read_long  (&num_to_skip, fp);
	write_long (&num_to_skip, stdout);
	while (num_to_skip--) 
	  fputc (fgetc (fp), stdout);
      }
      else {
	read_long  (&data_value, fp);
	write_long (&data_value, stdout);
      }
    }
  } while (TRUE);
}



