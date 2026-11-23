/*
=============================================================================
  KNOT.H
   A file describing a legal knot consists of
   1: how many strings,
       2: for each string, how many crossings, then
           3: for each crossing, the cross name, then 1 if over, -1 if under
   4: for each crossing, the name of the crossing and 1 if right, -1 if left.
   The spacing and placement of returns don't matter.  Integers only.
   If there are n crossings, they must be named 0..n-1.
   Example:  Two rubber bands, one on top of the other, would be:
   2

   4
   0  1   1  1   2  1   3  1
   4
   0 -1   1 -1   2 -1   3 -1

   0 -1
   1  1
   2 -1
   3  1
=============================================================================
*/
#ifndef LINK
#include "link.h"
#endif
#ifndef KNOT
#define KNOT

/*  The set of crossings for a link is represented by an array of
    type CROSSING.
    hand is -1 if this is crossing is lefthanded, 1 if it is righthanded.
    hand is  0 if the crossing no longer exists.
    o is a pointer to the overpass node.
    u is a pointer to the underpass node.                                 */

struct crossing
{
  link  *o;                                                      /* overpass */
  link  *u;                                                     /* underpass */
  int    hand;   /* 1 if right handed, -1 if left, 0 if no longer a crossing */
};
typedef struct crossing   crossing;


/* maximum number of crossings in a knot */
#define MAXCROSS 300

/* Procedures defined in knot.c */

void   k_show(/*_ int  crossings, crossing  *k _*/); /* Display a whole knot */
void   k_read(/*_ int *crossings, crossing **k _*/);     /* Read a knot file */


#endif /* ifndef KNOT */



