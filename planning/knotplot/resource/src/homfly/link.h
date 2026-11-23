/*
=============================================================================
  LINK.H
  Declares structures and procedures for the abstract data type LINK which is
  implemented in link.c .
=============================================================================
*/

#ifndef  LINK 
#define  LINK 

/*  Something of type LINK is a node in a doubly-linked cyclic list.
    C is the data stored in this node.
    A is a pointer to the previous node.
    Z is a pointer to the next node. */

struct link
{
  int           c;
  struct link  *a;
  struct link  *z;
};
typedef struct link   link;


/* Procedures defined in link.c */

# define l_init( l) (l = ((link *)(0)))
void   l_show(/*_ link *l _*/);                         /* Display all nodes */
void   l_add(/*_ link *inp, int c, link **outp _*/);           /* Add a node */
void   l_del(/*_ link **l _*/);                             /* Delete a node */

#endif  /* ifndef LINK */



