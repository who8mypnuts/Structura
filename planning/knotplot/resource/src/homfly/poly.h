/*
=============================================================================
  POLY.H
  Structures and procedures dealing with Laurent polynomials on M and L
  Laurent polynomials can have integer exponents; not just natural numbers.
  -(M^-1)(L^-1) - (M^-1)(L^1) is a typical polynomial of this type.
=============================================================================
*/

#ifndef POLY
#define POLY

/*=============================================================================
 Something of type TERM is a single term in a polynomial.
 coef is the coefficient of the term. (range is at least -64K .. 64K)
 L is the power of L in the term. (range is -128 to 127)
 M is the power of M in the term. (range is -128 to 127)
==========================================================================   */
struct term
{
  int    coef;
  char   m;                      /* 0..127 is positive, 128..255 is negative */
  char   l;                      /* 0..127 is positive, 128..255 is negative */
};
typedef struct term   term;


/*=============================================================================
  Something of type POLY is a polynomial of M and L.
  TERM is the array of terms.
  len is the number of terms.
==========================================================================   */
struct poly
{
  term  *term;
  int    len;
};
typedef struct poly   poly;


/*=============================================================================
  Procedures defined in poly.c
==========================================================================   */

#define p_init( p) ((p)->len = 0)

#define p_kill( p) \
if (1) \
{ \
  if ((p)->len) free((p)->term); \
  (p)->len = 0; \
} else

void   p_copy(/*_ poly *inp, poly *outp _*/);               /* copies a poly */
void   p_show(/*_ poly *l _*/);                         /* displays the poly */
void   p_add(/*_ poly *inp1, poly *inp2, poly *outp _*/);  /* adds two polys */
void   p_mult(/*_ poly *inp1, poly *inp2,
                  poly *outp _*/);                     /* multiply two polys */
void   p_term(/*_ int coef, int m, int l, 
                  poly *inp, 
                  poly *outp _*/);         /* returns a poly with term added */

#endif /* POLY */





