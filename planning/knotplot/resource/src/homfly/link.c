/* link.c - routines for dealing with doubly linked, circular lists */

#ifndef LINK
#include "link.h"
#endif

extern int work_quietly;

/*  This displays all the nodes in a single string */
void            l_show(l)
register link  *l;
{
  register link  *count;

  if ((count = l) != 0)
  {
    if (!work_quietly)  /* RGS mod */
      printf("%d ", count->c);
    count = count->z;
    while (count != l)
      {
	if (!work_quietly)  /* RGS mod */
	  printf("%d ", count->c);
	count = count->z;
      }
  }
  if (!work_quietly)  /* RGS mod */
    printf("\n");
}




/*  This takes a link inp, adds a link before it, and places a pointer to the
    added link in outp                                                      */
void            l_add(inp, crossings, outp)
register link  *inp;
int             crossings;
link          **outp;
{
  char           *malloc();
  register link  *newlink;

  newlink    = (link *)malloc(sizeof(link));
  newlink->c = crossings;
  if (inp == 0)
  {
    newlink->a = newlink;
    newlink->z = newlink;
    inp        = newlink;
  }
  else
  {
    newlink->a = inp->a;
    newlink->z = inp;
    inp->a->z  = newlink;
    inp->a     = newlink;
  }
  *outp = inp->a;
}




/*  This deletes a given link from a loop */

void   l_del(l)
link **l;
{
  register link  *ll = *l;

  if (!ll) return;
  if (ll->a != ll)
  {
    ll->z->a = ll->a;
    ll->a->z = ll->z;
  }
  free(ll);
  *l = (link *)0;
}




