#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#define TOTAL_NUMBER_KNOTS_IN_TABLE   383

/*       Number of crossings -----> 0  1  2  3  4  5  6  7   8   9   10   */

static int number_prime_knots [] = {1, 0, 0, 1, 1, 2, 3, 7, 21, 49, 165, /* 1  */
                                    1, 0, 1, 0, 1, 1, 3, 8, 16, 61,   0, /* 2  */
                                    1, 0, 0, 0, 0, 0, 3, 1, 10, 21,   0, /* 3  */
                                    1, 0, 0, 0, 0, 0, 0, 0,  3,  1,   0};/* 4  */
/*                                                                          |  */
/*                                                Number of components -----+  */

void rolfsen_table (int num, int *pncross, int *pid, int *pncomp) {
  int ncross = 0, index = 0, number, ncomp = 1;

  number = num;
  while (num > number_prime_knots [index]) {
    num -= number_prime_knots [index];
    ncross++;
    index++;
    if (ncross == 11) {
      ncross = 0;
      ncomp++;
      if (ncomp == 5) {
        fprintf (stderr, "Table doesn't go that far.\n");
	exit (102);
      }
    }
  }
  if (pid) *pid = num;
  if (pncross) *pncross = ncross;
  if (pncomp) *pncomp = ncomp;
}

#define TeX   0
#define HTML  1
#define BASIC 2
#define TOPO2 3


void table_info () {
  int ncross = 0, id, ncomp = 0, num;
  int last_ncross = -1, last_ncomp = -1;

  fprintf (stderr, "\nTable range is \n");

  for (num = 1; num <= TOTAL_NUMBER_KNOTS_IN_TABLE; num++) {
    rolfsen_table (num, &ncross, &id, &ncomp);
    if (ncross != last_ncross || 
	ncomp != last_ncomp) {
      if (num > 1) {
	fprintf (stderr, "%3d   %2d crossing ", num - 1, last_ncross);
	if (last_ncomp == 1)
	  fprintf (stderr, "proper knots\n");
	else
	  fprintf (stderr, "%d component links\n", last_ncomp);
      }
      fprintf (stderr, "   from %3d to ", num);
    }
    
    last_ncomp = ncomp; last_ncross = ncross;
  }
  fprintf (stderr, "%3d   %2d crossing %d component links\n\n", 
	   num - 1,
	   last_ncross,
	   last_ncomp);
  
}

void show_usage (char *s) {
  fprintf (stderr, "\n\n");
  fprintf (stderr, "Usage: %s  [options] number\n", s);
  fprintf (stderr, "       Prints alternate names for knots and links given the order in the catalogue.\n");
  fprintf (stderr, "       Options are:\n");
  fprintf (stderr, "       -html       HTML markup (the default)\n");
  fprintf (stderr, "       -tex        Tex/LaTeX format\n");
  fprintf (stderr, "       -basic      filename as found in the KnotPlot basic catalog\n");
  fprintf (stderr, "       -topo2      TopoII knot naming convention\n");
  fprintf (stderr, "       -n          don't print a new line character\n\n");
  fprintf (stderr, "       %s knotName\n", s);
  fprintf (stderr, "       Prints index of named knot in catalogue (example names: 3_1, 10.123)\n");
  table_info ();
  exit (102);
}

bool isKnotName (char *name) {
  int kount = 0;
  for (int i = 0; i < strlen (name); i++) {
    if (name [i] == '.' || name [i] == '_')
      kount++;
  }
  if (kount == 0)
    return false;

  if (kount < 3) {
    for (int i = 1; i <= TOTAL_NUMBER_KNOTS_IN_TABLE; i++) {
      int ncross; int id; int ncomp;
      rolfsen_table (i, &ncross, &id, &ncomp);
      if (kount == 1 && ncomp > 1 || kount > 1 && ncomp == 1)
	continue;
      char testname1 [20];
      char testname2 [20];
      if (kount == 1) {
	sprintf (testname1, "%d.%d", ncross, id);
	sprintf (testname2, "%d_%d", ncross, id);
      }
      else if (kount == 2) {
	sprintf (testname1, "%d.%d.%d", ncross, ncomp, id);
	sprintf (testname2, "%d_%d_%d", ncross, ncomp, id);
      }
      if (!strcmp (name, testname1) || !strcmp (name, testname2)) {
	printf ("%d\n", i);
	return true;
      }
    }
  }

  fprintf (stderr, "`%s' is not in the catalogue\n", name);
  return true;
}

int main (int c, char **v) {
  int num, ncross, id, ncomp, index;
  int mode = HTML;
  int new_line = 1;

  if (c < 2) 
    show_usage (v [0]);

  for (index = 1; index < c - 1; index++) {
    if (v [index][0] == '-') {
      if (!strcmp (v [index], "-tex")) 
	mode = TeX;
      else if (!strcmp (v [index], "-html"))
	mode = HTML;
      else if (!strcmp (v [index], "-basic"))
	mode = BASIC;
      else if (!strcmp (v [index], "-topoII") || !strcmp (v [index], "-topo2"))
	mode = TOPO2;
      else if (!strcmp (v [index], "-n"))
	new_line = 0;
      else {
	fprintf (stderr, "Unknown option.\n");
	show_usage (v [0]);
      }
    }
    else 
      break;
  }

  if (isKnotName (v [index]))
    return 1;

  num = atoi (v [index]);
  
  rolfsen_table (num, &ncross, &id, &ncomp);

  switch (mode) {
  case BASIC:
    if (ncomp == 1) 
      printf ("%d.%d", ncross, id);
    else
      printf ("%d.%d.%d", ncross, ncomp, id);
    break;
  case TOPO2:
    if (ncomp == 1) 
      printf ("%d_%d", ncross, id);
    else
      printf ("%d_%d_%d", ncross, ncomp, id);
    break;
  case HTML:
    if (ncomp == 1) 
      printf ("%d<sub>%d</sub>", ncross, id);
    else
      printf ("%d<sup>%d</sup><sub>%d</sub>", ncross, ncomp, id);
    break;
  case TeX:
    if (ncomp == 1) 
      printf ("%d_{%d}", ncross, id);
    else
      printf ("%d^{%d}_{%d}", ncross, ncomp, id);
    break;
  }
  if (new_line) printf ("\n");

  return 1;
}

