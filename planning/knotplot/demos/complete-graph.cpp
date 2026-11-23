#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*  example, K6
 
   0   1   2   3   4   5 l

0  x   0   1   2   3   4

1  x   x   5   6   7   8

2  x   x   x   9  10  11

3  x   x   x   x  12  13

4  x   x   x   x   x  14

5  x   x   x   x   x   x

f

Aliases for nodes:
0 f0
1 l0
2 l1
3 l2
4 l3
5 l4

*/

int main (int argc, char **argv) {
  int N;

  N = atoi (argv [1]);
  printf ("frame 0 num %d\n", (N * N - N) / 2);


  int index = 0;
  
  for (int from_node = 0; from_node < N; from_node++)
    for (int to_node = from_node + 1; to_node < N; to_node++, index++) {
      /*
      if (to_node > from_node + 1) {
	printf ("iden f%d f%d\n", index, index - to_node + 1 + from_node); 
      }
      */

      char s1 [10], s2 [10];

      sprintf (s1, "f%d", index);
      if (from_node == 0)
	strcpy (s2, "f0");
      else
	sprintf (s2, "l%d", from_node - 1);

      if (strcmp (s1, s2))
	printf ("iden %s %s\n", s1, s2);

      sprintf (s1, "l%d", index);

      if (to_node == 0)
	strcpy (s2, "f0");
      else
	sprintf (s2, "l%d", to_node - 1);
      
      if (strcmp (s1, s2))
	printf ("iden %s %s\n", s1, s2);

    }
}

