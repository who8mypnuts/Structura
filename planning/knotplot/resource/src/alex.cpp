/*

This is the auxilary program that KnotPlot calls to help in 
evaluating the Alexander polynomial.  
To see how its called, enter into KnotPlot

  Debug=t

before running the alex command. 

                          --- Rob Scharein
                              8 Feb 2005

*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAPLE 1
#define MATHM 2

int main (int argc, char **argv) {
  int *csign = (int *) NULL;
  int *bridge = (int *) NULL;
  int *a = (int *) NULL;
  int ncross;
  int i, j, k, kp1;
  FILE *fp;
  int outputf = MAPLE;
  
  for (i = 1; i < argc; i++) {
    if (argv [i][0] != '-') break;
    if (!strcmp (argv [i], "-mathm")) outputf = MATHM;
    if (!strcmp (argv [i], "-maple")) outputf = MAPLE;
  }
  
  if (argc > i) {
    fp = fopen (argv [i], "r");
    if (!fp) {
      fprintf (stderr, "\n *** %s: Can't open file `%s'.\n", argv [0], argv [1]);
      goto endgame;
    }
  }
  else
    fp = stdin;
  
  fscanf (fp, "%d", &ncross);
  csign = (int *) calloc (ncross + 2, sizeof (int));
  bridge = (int *) calloc (ncross + 2, sizeof (int));
  a = (int *) calloc ((ncross + 2) * (ncross + 2), sizeof (int));
  if (!a || !csign || !bridge) {
    fprintf (stderr, "\n *** %s: Can't get enough memory!\n", argv [0]);
    goto endgame;
  }
  
  
  for (j = 1; j <= ncross; j++) 
    fscanf (fp, "%d%d", bridge + j, csign + j);
  
  for (k = 1; k <= ncross; k++)
    for (j = 1; j <= ncross; j++) 
      a [k * ncross + j] = 0;
    
    for (k = 1; k <= ncross; k++) {
      i = bridge [k];
      kp1 = (k % ncross) + 1;
      for (j = 1; j <= ncross; j++) {      
        if (csign [k] == 1) {
          if (i == k || i == kp1) {
            a [k * ncross + k] = -1;
            a [k * ncross + kp1] = 1;
          }
          else {
            a [k * ncross + k] = 1;
            a [k * ncross + kp1] = 2;
            a [k * ncross + i] = 3;
          }
        }
        else {
          if (i == k || i == kp1) {
            a [k * ncross + k] = -1;
            a [k * ncross + kp1] = 1;
          }
          else {
            a [k * ncross + k] = 2;
            a [k * ncross + kp1] = 1;
            a [k * ncross + i] = 3;
          }
        }
      }
    }
    
    switch (outputf) {
    case MAPLE:
      printf ("with(linalg);\n");
      
      for (k = 1; k < ncross; k++) {
        printf ("r%d := array (1..%d, [", k, ncross - 1); 
        for (j = 1; j < ncross; j++) {
          switch (a [k * ncross + j]) {
          case 2:
            printf ("-t"); 
            break;
          case 3:
            printf ("t-1");
            break;
          default:
            printf ("%d", a [k * ncross + j]);
            break;
          }
          if (j == ncross - 1) 
            printf ("]);\n");
          else 
            printf (", ");
        }
      }
      
      printf ("m := matrix (%d, %d, [", ncross - 1, ncross - 1);
      for (j = 1; j < ncross; j++) {
        printf ("r%d", j);
        if (j == ncross - 1) 
          printf ("]);\n");
        else 
          printf (", ");
      }
      
      printf ("a := det (m);\n");
      /*  //printf ("c := [coeffs(a)];\n");*/
      printf ("c := [seq(coeff(a,t,i), i = ldegree(a)..degree(a))];\n");
      printf ("n := nops(c);\n");
      printf ("f := floor(n/2);\n");
      printf ("p := c[f+1..n];\n");
      printf ("s := sign(p[1]);\n");
      printf ("KPalex := map(x->x * s, p);\n");
      printf ("KPdet := abs(eval(a,t=-1));\n");
      printf ("printf (\"KnotPlot poly is %%a\\nKnotPlot Det = %%d\\n\", KPalex, KPdet);\n");
      break;
      
    case MATHM:
      for (k = 1; k < ncross; k++) {
        printf ("r%d = {", k); 
        for (j = 1; j < ncross; j++) {
          switch (a [k * ncross + j]) {
          case 2:
            printf ("-t"); 
            break;
          case 3:
            printf ("t-1");
            break;
          default:
            printf ("%d", a [k * ncross + j]);
            break;
          }
          if (j == ncross - 1) 
            printf ("};\n");
          else 
            printf (", ");
        }
      }
      
      printf ("m = {");
      for (j = 1; j < ncross; j++) {
        printf ("r%d", j);
        if (j == ncross - 1) 
          printf ("};\n");
        else 
          printf (", ");
      }
      
      printf ("d = Det[m]\n");
      printf ("cz = CoefficientList[d, t];\n");
      printf ("remZ[x_] := If [First [x] == 0, remZ[Rest[x]], x]\n");
      printf ("c = remZ[cz];\n");
      printf ("len = Length[c];\n");
      printf ("a = If [OddQ [len], Take [c, -(Floor[len/2] +1)], error];\n");
      printf ("ap = a Sign[First[a]]\n");
      printf ("Factor[d]\n");
      printf ("x = Abs[d] /. t -> -1\n");
      printf ("Print[\"\\nKnotPlot poly is \" <> ToString [TeXForm [d]]]\n");
      printf ("Print[\"\\nKnotPlot Det is \" <> ToString[x]]\n"); 
      
      break;
    }
    
endgame:
    if (a) free (a);
    if (bridge) free (bridge);
    if (csign) free (csign);
    
    return 0;
}

