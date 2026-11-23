/*  By Bob Jenkins, in relation to my Master's Thesis */
/*  This module handles entire knots.                 */

#ifndef STANDARD
#include "standard.h"
#endif
#ifndef LINK
#include "link.h"
#endif
#ifndef KNOT
#include "knot.h"
#endif

extern int work_quietly;

/*  Assumes the links all form cycles                                 */
/*  This displays each string once by listing its crossings in order.
    After that, it displays the HANDedness of each crossing.          */

void       k_show(crossings, k)
int        crossings;
crossing  *k;
{
  int    i,
         j;
  int    tab[MAXCROSS];
  link  *count,
        *start;

  for (i = 0; i < crossings; i++) tab[i] = 0;
  for (j = 0; j < 2; j++)
  {
    for (i = 0; i < crossings; i++)
    {
      if (k[i].hand && ((tab[i] == 0) || (tab[i] == 1) || (tab[i] == 10)))
      {
        if (tab[i] != 10) count = k[i].o;
        else count = k[i].u;
        start = count;
        if (count != 0 && !work_quietly) printf("%d ", count->c);
        if (k[count->c].o == count)
        {
	  if (!work_quietly)
	    printf("1   ");
          tab[count->c] += 10;
        }
        else
        {
	  if (!work_quietly)
	    printf("-1  ");
          tab[count->c] += 1;
        }
        if (count != 0) count = count->z;
        while (count != start)
        {
	  if (!work_quietly)
	    printf("%d ", count->c);
          if (k[count->c].o == count)
          {
	    if (!work_quietly)
	      printf("1   ");
            tab[count->c] += 10;
          }
          else
          {
	    if (!work_quietly)
	      printf("-1  ");
            tab[count->c] += 1;
          }
          count = count->z;
        }
      }
      if (!work_quietly)
	printf("\n");
    }
  }
  if (!work_quietly)
    printf("\n");
  for (i = 0; i < crossings; i++)
  {
    if (k[i].hand == 1) printf("%d : right\n", i);
    else if (k[i].hand == (-1)) printf("%d : left\n", i);
  }
  if (!work_quietly)
    printf("\n");
}




/*  Assumes the file given by the user exists and contains a legal knot.  */

void       k_read(crossings, kk, from_stdin) /* RGS mod */
int       *crossings;
crossing **kk;
int from_stdin;   /* RGS mod */
{
  char       name[20];
  ub4        links,
             startwhere,
             where,
             startover,
             over,
             i;
  crossing   k[MAXCROSS];
  FILE      *f;

  for (i = 0; i < MAXCROSS; i++) k[i].hand = 0;

  if (from_stdin)  /* RGS mod */
    f = stdin;
  else {
    printf("Enter name of knot file: ");
    scanf("%s", name);
    f = fopen(name, "r");
    if (f == 0)
      {
	printf("Can't find %s \n", name);
	fclose(f);
	return;
      }
  }

  fscanf(f, "%d ", &links);
  for (; links > 0; --links)                    /* how many pieces of string */
  {
    fscanf(f, "%d ", crossings);
    fscanf(f, "%d %d ", &startwhere, &startover);
    if (startover == 1) l_add(0, startwhere, &k[startwhere].o);
    else l_add(0, startwhere, &k[startwhere].u);
    for (; *crossings > 1; --(*crossings))
    {
      fscanf(f, "%d %d ", &where, &over);
      if (over == 1)
      {
        if (startover == 1) l_add(k[startwhere].o, where, &k[where].o);
        else l_add(k[startwhere].u, where, &k[where].o);
      }
      else
      {
        if (startover == 1) l_add(k[startwhere].o, where, &k[where].u);
        else l_add(k[startwhere].u, where, &k[where].u);
      }
    }
  }
  *crossings = 0;
  while (fscanf(f, "%d %d ", &where, &over) == 2)
  {
    k[where].hand = over;
    if (where > *crossings) *crossings = where;
  }
  (*crossings)++;
  if (!from_stdin)    /* RGS mod */
    i = fclose(f);
  *kk = (crossing *)malloc((sizeof(crossing))*(*crossings));
  for (i = 0; i < (*crossings); i++) (*kk)[i] = k[i];
}








