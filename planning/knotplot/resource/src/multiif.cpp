#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/*

  Generates cumbersome KnotPlot command script to
  implement a sort of computed go to.
  Each option can have a different relative 
  probability.
  
  Example input file:

par1
3 read gumby.kps
4 info;length;thickness
5 read pokey.kps
1 reset all
6 read goo.kps
2 knot
4 read zviegie.kps


and corresponding output:

par1 = \rr25
if par1 < 3 then "read gumby.kps;par1=27"
if par1 < 7 then "info;length;thickness;par1=27"
if par1 < 12 then "read pokey.kps;par1=27"
if par1 < 13 then "reset all;par1=27"
if par1 < 19 then "read goo.kps;par1=27"
if par1 < 21 then "knot;par1=27"
if par1 < 26 then "read zviegie.kps;par1=27"


Note that relative probabilities should be integers.
Also, use "read" instead of "<".

*/

typedef struct {
  double p;
  char s [108];
} Option;

#define MAXOP 102

Option option [MAXOP];

int main (int argc, char **argv) {
  char par [102];
  char in_line [333];
  double total_p = 0.0;
  FILE *fp;
  time_t the_time;

  if (argc < 2) {
    fprintf (stderr, "Usage: %s file\n", argv [0]);
    exit (1022);
  }

  fp = fopen (argv [1], "r");
  if (!fp) {
    fprintf (stderr, "Can't open file `%s'.\n", argv [1]);
    exit (102);
  }

  time (&the_time);
  printf ("%%%% Generated %s", ctime (&the_time));
  printf ("%%%% with command line: %s %s\n", argv [0], argv [1]);
  printf ("parsave\n");
  fgets (in_line, 102, fp);
  sscanf (in_line, "%s", par);

  int index = 0;
  while (fgets (in_line, 102, fp)) {
    sscanf (in_line, "%lf", &option [index].p);
    
    char *s = in_line;
    while (*s != ' ') s++;  // look for first blank
    while (*s == ' ' || *s == '\t') s++;  // skip blanks and tabs
    
    strcpy (option [index].s, s);
    int len = strlen (option [index].s);
    option [index].s [len - 1] = '\0';
    total_p += option [index].p;
    index++;
  }

  fclose (fp);

  int nops = index;

  printf ("%s = \\rr%.0f\n", par, total_p);
  double accum_p = 0.0;

  for (index = 0; index < nops; index++) {
    accum_p += option [index].p;
    if (index == nops - 1) accum_p += 1.0;

    printf ("if %s < %.0f then \"%s;%s=%.0f\"\n", 
      par, accum_p, option [index].s, par, total_p + 2.0);
  }


  printf ("parrestore\n");

  return 0;

}

